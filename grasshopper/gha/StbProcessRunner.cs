using System;
using System.Diagnostics;
using System.IO;

namespace StbGrasshopper
{
    public static class StbProcessRunner
    {
        public static StbAnalyzeResult Analyze(
            string datPath,
            string pythonExe,
            string repoRoot,
            bool run,
            string outPath,
            int? loadCase = null)
        {
            if (!run)
            {
                return new StbAnalyzeResult
                {
                    Success = false,
                    ExitCode = -1,
                    OutPath = outPath ?? string.Empty,
                    Summary = "run is False; STB was not executed."
                };
            }

            if (string.IsNullOrWhiteSpace(datPath))
            {
                return new StbAnalyzeResult
                {
                    Success = false,
                    ExitCode = 1,
                    Summary = "DAT path is empty. Set STB Assemble Write to true first."
                };
            }

            datPath = Path.GetFullPath(datPath);
            outPath = string.IsNullOrWhiteSpace(outPath) ? DefaultOutputPath(datPath) : Path.GetFullPath(outPath);

            string resolveError;
            if (!TryResolveInterpreter(ref pythonExe, ref repoRoot, out resolveError))
            {
                return new StbAnalyzeResult
                {
                    Success = false,
                    ExitCode = 1,
                    OutPath = outPath,
                    Stderr = resolveError,
                    Summary = "Structural Toolbox Python was not found."
                };
            }

            if (!File.Exists(datPath))
            {
                return new StbAnalyzeResult
                {
                    Success = false,
                    ExitCode = 1,
                    OutPath = outPath,
                    Stderr = "Input file not found: " + datPath,
                    Summary = "STB input file was not found."
                };
            }

            Directory.CreateDirectory(Path.GetDirectoryName(outPath));

            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                WorkingDirectory = repoRoot,
                Arguments = "-m stb_cli solve " + Quote(datPath) + " -o " + Quote(outPath) + " -q -v",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };

            // The PC's own Python settings make the bundled interpreter load a
            // foreign standard library and crash.
            foreach (var name in new[] { "PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONUSERBASE", "VIRTUAL_ENV" })
            {
                psi.Environment.Remove(name);
            }

            psi.Environment["PYTHONNOUSERSITE"] = "1";

            using (var process = Process.Start(psi))
            {
                var stdout = process.StandardOutput.ReadToEnd();
                var stderr = process.StandardError.ReadToEnd();
                process.WaitForExit();

                if (process.ExitCode != 0)
                {
                    return new StbAnalyzeResult
                    {
                        Success = false,
                        ExitCode = process.ExitCode,
                        OutPath = outPath,
                        Stdout = stdout,
                        Stderr = stderr,
                        Summary = "STB solve failed with exit code " + process.ExitCode
                    };
                }

                var parsed = StbOutParser.ParseFile(outPath, loadCase);
                StbDatParser.ReadGeometry(datPath, out var nodes, out var elements);
                parsed.DatPath = datPath;
                parsed.Nodes.AddRange(nodes);
                parsed.Elements.AddRange(elements);

                return new StbAnalyzeResult
                {
                    Success = true,
                    ExitCode = process.ExitCode,
                    DatPath = datPath,
                    OutPath = outPath,
                    Stdout = stdout,
                    Stderr = stderr,
                    Results = parsed,
                    Summary =
                        "Solved "
                        + Path.GetFileName(datPath)
                        + "; nodes="
                        + parsed.Nodes.Count
                        + "; elements="
                        + parsed.Elements.Count
                        + "; displacements="
                        + parsed.Displacements.Count
                        + "; python="
                        + pythonExe
                };
            }
        }

        /// <summary>
        /// Finds the Python that ships with Structural Toolbox. A Python the
        /// student installed for another course would lack the solver
        /// libraries, so this never falls back to one found on PATH.
        /// </summary>
        private static bool TryResolveInterpreter(
            ref string pythonExe,
            ref string repoRoot,
            out string error)
        {
            error = null;

            if (!string.IsNullOrWhiteSpace(pythonExe))
            {
                pythonExe = Path.GetFullPath(pythonExe);
                if (!File.Exists(pythonExe))
                {
                    error = "Python Exe was set but does not exist: " + pythonExe;
                    return false;
                }
                if (string.IsNullOrWhiteSpace(repoRoot))
                {
                    repoRoot = InstallRootOf(pythonExe);
                }
                repoRoot = Path.GetFullPath(repoRoot);
                return true;
            }

            foreach (var root in CandidateRoots(repoRoot))
            {
                var found = VenvPython(root);
                if (found != null)
                {
                    pythonExe = found;
                    repoRoot = root;
                    return true;
                }
            }

            error =
                "Structural Toolbox Python was not found. Run the first-time setup "
                + "(Install_once) from the install folder, or set Python Exe to the "
                + VenvRelativePath()
                + " of the install. Looked in: "
                + string.Join("; ", CandidateRoots(repoRoot));
            return false;
        }

        private static string[] CandidateRoots(string repoRoot)
        {
            var roots = new System.Collections.Generic.List<string>();

            if (!string.IsNullOrWhiteSpace(repoRoot))
            {
                roots.Add(Path.GetFullPath(repoRoot));
            }

            // Install folder used by the student installers.
            var appSupport = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (!string.IsNullOrWhiteSpace(appSupport))
            {
                roots.Add(Path.Combine(appSupport, "StructuralToolbox"));
            }
            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            if (!string.IsNullOrWhiteSpace(home))
            {
                roots.Add(Path.Combine(home, "Library", "Application Support", "StructuralToolbox"));
            }

            // Folder this .gha was loaded from, for developer checkouts.
            var here = Path.GetDirectoryName(typeof(StbProcessRunner).Assembly.Location);
            while (!string.IsNullOrWhiteSpace(here))
            {
                roots.Add(here);
                here = Path.GetDirectoryName(here);
            }

            var unique = new System.Collections.Generic.List<string>();
            foreach (var root in roots)
            {
                if (!string.IsNullOrWhiteSpace(root) && !unique.Contains(root))
                {
                    unique.Add(root);
                }
            }
            return unique.ToArray();
        }

        private static string VenvPython(string root)
        {
            var candidates = new[]
            {
                Path.Combine(root, ".venv", "Scripts", "python.exe"),
                Path.Combine(root, ".venv", "bin", "python3"),
                Path.Combine(root, ".venv", "bin", "python")
            };
            foreach (var candidate in candidates)
            {
                if (File.Exists(candidate))
                {
                    return candidate;
                }
            }
            return null;
        }

        private static string VenvRelativePath()
        {
            return Path.DirectorySeparatorChar == '\\'
                ? ".venv\\Scripts\\python.exe"
                : ".venv/bin/python3";
        }

        private static string InstallRootOf(string pythonExe)
        {
            // <root>/.venv/Scripts/python.exe or <root>/.venv/bin/python3
            var dir = Path.GetDirectoryName(pythonExe);
            var venv = Path.GetDirectoryName(dir);
            var root = Path.GetDirectoryName(venv);
            return string.IsNullOrWhiteSpace(root) ? Path.GetDirectoryName(pythonExe) : root;
        }

        private static string DefaultOutputPath(string datPath)
        {
            var outDir = Path.Combine(Path.GetTempPath(), "stb_gh");
            Directory.CreateDirectory(outDir);
            return Path.Combine(outDir, Path.GetFileNameWithoutExtension(datPath) + ".out");
        }

        private static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }
    }
}
