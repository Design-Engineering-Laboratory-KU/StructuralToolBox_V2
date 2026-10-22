using System;
using System.Reflection;
using Grasshopper.Kernel;

namespace StbGrasshopper
{
    public sealed class StbGrasshopperInfo : GH_AssemblyInfo
    {
        public override string Name => "STB Grasshopper";
        public override string Description => "Grasshopper components for Structural Toolbox.";
        public override Guid Id => new Guid("984f5847-93df-4f6f-8da7-645af10d7394");
        public override string AuthorName => "Structural Toolbox";
        public override string AuthorContact => string.Empty;
        public override string Version =>
            typeof(StbGrasshopperInfo).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion
            ?? string.Empty;
    }
}
