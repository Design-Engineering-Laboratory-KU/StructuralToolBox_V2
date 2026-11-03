import test from "node:test";
import assert from "node:assert/strict";

import {
  breakpoints,
  forceSegments,
  sampleStations,
  sectionForceAt,
} from "../../stb_gui/static/section_forces.js";

function close(actual, expected, tol = 1e-10) {
  assert.ok(
    Math.abs(actual - expected) <= tol * Math.max(1, Math.abs(expected)),
    `${actual} != ${expected}`
  );
}

test("simply supported beam under a uniform load", () => {
  const len = 8;
  const w = 12;
  const f = [0, 0, w * len / 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
  const segs = [[0, 1, 0, 0, -w, 0, 0, -w]];
  for (const t of [0, 0.2, 0.5, 0.8, 1]) {
    const x = t * len;
    close(sectionForceAt(f, len, segs, t).My, w * x * (len - x) / 2);
  }
});

test("partial uniform load contributes only after its start", () => {
  const f = Array(14).fill(0);
  const segs = [[0.2, 0.4, 0, 2, 0, 0, 2, 0]];
  close(sectionForceAt(f, 10, segs, 0.1).Qy, 0);
  close(sectionForceAt(f, 10, segs, 0.3).Qy, 2);
  close(sectionForceAt(f, 10, segs, 0.3).Mz, -1);
  close(sectionForceAt(f, 10, segs, 0.6).Qy, 4);
  close(sectionForceAt(f, 10, segs, 0.6).Mz, -12);
});

test("two segments form a triangular load", () => {
  const f = Array(14).fill(0);
  const segs = [
    [0, 0.5, 0, 0, 0, 0, 4, 0],
    [0.5, 1, 0, 4, 0, 0, 0, 0],
  ];
  const end = sectionForceAt(f, 10, segs, 1);
  close(end.Qy, 20);
  close(end.Mz, -100);
});

test("point load makes a jump in shear and a kink in moment", () => {
  const len = 6;
  const P = -12;
  const t = 0.25;
  // simply supported: Qz at i equals the reaction at i
  const f = [0, 0, -P * (1 - t), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
  const segs = [[t, t, 0, 0, P, 0, 0, P]];
  close(sectionForceAt(f, len, segs, t - 1e-6).Qz, -P * (1 - t));
  close(sectionForceAt(f, len, segs, t + 1e-6).Qz, -P * (1 - t) + P);
  close(sectionForceAt(f, len, segs, t).My, -P * (1 - t) * t * len);
  close(sectionForceAt(f, len, segs, 1).My, 0, 1e-9);
  assert.deepEqual(sampleStations(2, segs), [0, t - 1e-6, t, t + 1e-6, 0.5, 1]);
});

test("point load at the member ends", () => {
  const f = Array(14).fill(0);
  close(sectionForceAt(f, 10, [[0, 0, 0, 3, 0, 0, 3, 0]], 0).Qy, 3);
  close(sectionForceAt(f, 10, [[1, 1, 0, 3, 0, 0, 3, 0]], 1).Qy, 0);
  assert.deepEqual(breakpoints([[0, 0, 0, 3, 0, 0, 3, 0]]), [1e-6]);
});

test("breakpoints and uniform stations are sorted and merged", () => {
  const segs = [
    [0.2, 0.4, 0, 0, 0, 0, 0, 0],
    [0.4000000005, 0.75, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0, 0, 0],
  ];
  assert.deepEqual(breakpoints(segs), [0.2, 0.4, 0.75]);
  assert.deepEqual(sampleStations(4, segs), [0, 0.2, 0.25, 0.4, 0.5, 0.75, 1]);
});

test("local_wloads fallback applies member sign only to wy and wz", () => {
  const e = { local_wloads: { "3": [1, 2, 3, 4, 5, 6] } };
  assert.deepEqual(
    forceSegments(e, "3", () => -1),
    [[0, 1, 1, -2, -3, 4, -5, -6]]
  );
  assert.deepEqual(forceSegments({ ...e, wsegs: { "3": [] } }, "3", () => -1), []);
});
