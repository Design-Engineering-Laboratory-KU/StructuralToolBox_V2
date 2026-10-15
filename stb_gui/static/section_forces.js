const MERGE_TOL = 1e-9;

export function forceSegments(e, lcKey, memberLoadSignFn) {
  if (e && e.wsegs != null) {
    return e.wsegs[lcKey] || [];
  }
  const w = e && e.local_wloads && e.local_wloads[lcKey];
  if (!w) return [];
  const sign = memberLoadSignFn ? memberLoadSignFn(e) : 1;
  return [[0, 1, w[0], sign * w[1], sign * w[2], w[3], sign * w[4], sign * w[5]]];
}

function segmentIntegrals(seg, len, x) {
  const t0 = Number(seg[0]);
  const t1 = Number(seg[1]);
  const a = t0 * len;
  const b = t1 * len;
  const u = Math.min(b, x);
  if (!(u > a) || !(b > a)) return [[0, 0, 0], [0, 0, 0]];

  const d = u - a;
  const xa = x - a;
  const i0 = [0, 0, 0];
  const i1 = [0, 0, 0];
  for (let c = 0; c < 3; c++) {
    const wa = Number(seg[2 + c]) || 0;
    const wb = Number(seg[5 + c]) || 0;
    const slope = (wb - wa) / (b - a);
    i0[c] = wa * d + 0.5 * slope * d * d;
    i1[c] = xa * i0[c] - 0.5 * wa * d * d - (slope * d * d * d) / 3;
  }
  return [i0, i1];
}

export function sectionForceAt(f, len, segs, t) {
  const x = Math.max(0, Math.min(1, Number(t))) * len;
  const i0 = [0, 0, 0];
  const i1 = [0, 0, 0];
  for (const seg of segs || []) {
    const ints = segmentIntegrals(seg, len, x);
    for (let c = 0; c < 3; c++) {
      i0[c] += ints[0][c];
      i1[c] += ints[1][c];
    }
  }
  return {
    N: f[0] - i0[0],
    Qy: f[1] + i0[1],
    Qz: f[2] + i0[2],
    Mx: f[3],
    My: f[4] + f[2] * x + i1[2],
    Mz: f[5] - f[1] * x - i1[1],
  };
}

export function breakpoints(segs) {
  const values = [];
  for (const seg of segs || []) {
    for (const value of [Number(seg[0]), Number(seg[1])]) {
      if (value > 0 && value < 1) values.push(value);
    }
  }
  values.sort(function (a, b) { return a - b; });
  return values.filter(function (value, i) {
    return i === 0 || Math.abs(value - values[i - 1]) >= MERGE_TOL;
  });
}

export function sampleStations(divNum, segs) {
  const n = Math.max(1, Math.floor(Number(divNum) || 1));
  const values = [];
  for (let k = 0; k <= n; k++) values.push(k / n);
  values.push(...breakpoints(segs));
  values.sort(function (a, b) { return a - b; });
  return values.filter(function (value, i) {
    return i === 0 || Math.abs(value - values[i - 1]) >= MERGE_TOL;
  });
}
