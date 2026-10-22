using System;
using Rhino.Geometry;

namespace StbGrasshopper
{
    /// <summary>Member axes as classes/elm.py Elm1D.CalcBeta (Beta in degrees).</summary>
    internal static class StbMemberAxes
    {
        private const double PresAngle = 0.001;

        public static void Compute(Line line, double betaDegrees, out Vector3d x, out Vector3d y, out Vector3d z)
        {
            x = line.Direction;
            x.Unitize();
            var beta = betaDegrees * Math.PI / 180.0;
            var angle = Vector3d.VectorAngle(x, Vector3d.ZAxis);

            if (angle < PresAngle || Math.Abs(angle - Math.PI) < PresAngle)
            {
                var alpha = Math.Abs(angle - Math.PI) < PresAngle ? 0.5 * Math.PI : -0.5 * Math.PI;
                y = Vector3d.XAxis;
                y.Rotate(beta + alpha, x);
            }
            else
            {
                y = Vector3d.CrossProduct(Vector3d.ZAxis, x);
                y.Unitize();
                y.Rotate(beta, x);
            }

            z = Vector3d.CrossProduct(x, y);
            z.Unitize();
        }

        /// <summary>True for members parallel to global Z, either way up (elm.py isVxZ).</summary>
        public static bool IsVertical(Line line)
        {
            var x = line.Direction;
            x.Unitize();
            var angle = Vector3d.VectorAngle(x, Vector3d.ZAxis);
            return angle < PresAngle || Math.Abs(angle - Math.PI) < PresAngle;
        }
    }
}
