if (-not ('EiBatchV2.ImagePreprocessor' -as [type])) {
    Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Drawing;

namespace EiBatchV2 {
    public sealed class PreparedImage {
        public byte[] Rgb { get; set; }
        public int SourceWidth { get; set; }
        public int SourceHeight { get; set; }
        public int ResizeWidth { get; set; }
        public int ResizeHeight { get; set; }
        public int PadX { get; set; }
        public int PadY { get; set; }
    }

    public static class ImagePreprocessor {
        private const int TargetWidth = 160;
        private const int TargetHeight = 160;
        private const int FractionBits = 14;
        private const uint FractionValue = 1U << FractionBits;
        private const uint FractionMask = FractionValue - 1U;

        private static byte Interpolate(
            byte p00,
            byte p10,
            byte p01,
            byte p11,
            uint xFraction,
            uint yFraction)
        {
            uint nextXFraction = FractionValue - xFraction;
            uint nextYFraction = FractionValue - yFraction;
            uint top = ((uint)p00 * nextXFraction +
                        (uint)p10 * xFraction + FractionValue / 2U) >> FractionBits;
            uint bottom = ((uint)p01 * nextXFraction +
                           (uint)p11 * xFraction + FractionValue / 2U) >> FractionBits;
            uint value = (top * nextYFraction +
                          bottom * yFraction + FractionValue / 2U) >> FractionBits;
            return (byte)value;
        }

        public static PreparedImage Convert(string sourcePath)
        {
            using (Bitmap bitmap = new Bitmap(sourcePath)) {
                int sourceWidth = bitmap.Width;
                int sourceHeight = bitmap.Height;
                float sourceAspect = (float)sourceWidth / sourceHeight;
                float targetAspect = (float)TargetWidth / TargetHeight;
                int resizeWidth;
                int resizeHeight;

                if (sourceAspect > targetAspect) {
                    resizeWidth = TargetWidth;
                    resizeHeight = (int)(TargetWidth / sourceAspect);
                }
                else {
                    resizeHeight = TargetHeight;
                    resizeWidth = (int)(TargetHeight * sourceAspect);
                }

                int padX = (TargetWidth - resizeWidth) / 2;
                int padY = (TargetHeight - resizeHeight) / 2;
                uint sourceXFraction =
                    (uint)(sourceWidth * FractionValue / resizeWidth);
                uint sourceYFraction =
                    (uint)(sourceHeight * FractionValue / resizeHeight);
                byte[] rgb = new byte[TargetWidth * TargetHeight * 3];
                uint sourceYAccumulator = 0;

                for (int y = 0; y < resizeHeight; ++y) {
                    int sourceY = (int)(sourceYAccumulator >> FractionBits);
                    uint yFraction = sourceYAccumulator & FractionMask;
                    sourceYAccumulator += sourceYFraction;
                    uint sourceXAccumulator = 0;

                    for (int x = 0; x < resizeWidth; ++x) {
                        int sourceX = (int)(sourceXAccumulator >> FractionBits);
                        uint xFraction = sourceXAccumulator & FractionMask;
                        sourceXAccumulator += sourceXFraction;

                        int sourceX1 = Math.Min(sourceX + 1, sourceWidth - 1);
                        int sourceY1 = Math.Min(sourceY + 1, sourceHeight - 1);
                        Color p00 = bitmap.GetPixel(sourceX, sourceY);
                        Color p10 = bitmap.GetPixel(sourceX1, sourceY);
                        Color p01 = bitmap.GetPixel(sourceX, sourceY1);
                        Color p11 = bitmap.GetPixel(sourceX1, sourceY1);
                        int destinationIndex =
                            ((padY + y) * TargetWidth + padX + x) * 3;

                        rgb[destinationIndex] = Interpolate(
                            p00.R, p10.R, p01.R, p11.R, xFraction, yFraction);
                        rgb[destinationIndex + 1] = Interpolate(
                            p00.G, p10.G, p01.G, p11.G, xFraction, yFraction);
                        rgb[destinationIndex + 2] = Interpolate(
                            p00.B, p10.B, p01.B, p11.B, xFraction, yFraction);
                    }
                }

                return new PreparedImage {
                    Rgb = rgb,
                    SourceWidth = sourceWidth,
                    SourceHeight = sourceHeight,
                    ResizeWidth = resizeWidth,
                    ResizeHeight = resizeHeight,
                    PadX = padX,
                    PadY = padY
                };
            }
        }

        public static uint Crc32(byte[] data)
        {
            uint crc = 0xFFFFFFFFU;
            for (int index = 0; index < data.Length; ++index) {
                crc ^= data[index];
                for (int bit = 0; bit < 8; ++bit) {
                    uint mask = (uint)-(int)(crc & 1U);
                    crc = (crc >> 1) ^ (0xEDB88320U & mask);
                }
            }
            return ~crc;
        }
    }
}
'@
}

function ConvertTo-EiV2Rgb888 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath
    )

    $resolvedSource = (Resolve-Path -LiteralPath $SourcePath).Path
    return [EiBatchV2.ImagePreprocessor]::Convert($resolvedSource)
}

function Get-EiV2Crc32 {
    param(
        [Parameter(Mandatory = $true)]
        [byte[]]$Data
    )

    return [EiBatchV2.ImagePreprocessor]::Crc32($Data)
}

Export-ModuleMember -Function ConvertTo-EiV2Rgb888, Get-EiV2Crc32
