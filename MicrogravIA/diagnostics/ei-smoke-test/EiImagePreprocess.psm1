if (-not ('EiBatch.ImagePreprocessor' -as [type])) {
    Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Drawing;

namespace EiBatch {
    public sealed class PreparedImage {
        public byte[] Rgb { get; set; }
        public int SourceWidth { get; set; }
        public int SourceHeight { get; set; }
        public int CropX { get; set; }
        public int CropY { get; set; }
        public int CropWidth { get; set; }
        public int CropHeight { get; set; }
    }

    public static class ImagePreprocessor {
        private const int TargetWidth = 96;
        private const int TargetHeight = 96;
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
                int cropWidth;
                int cropHeight;

                if (sourceWidth > sourceHeight) {
                    cropWidth = TargetWidth * sourceHeight / TargetHeight;
                    cropHeight = sourceHeight;
                }
                else {
                    cropHeight = TargetHeight * sourceWidth / TargetWidth;
                    cropWidth = sourceWidth;
                }

                int cropX = (sourceWidth - cropWidth) / 2;
                int cropY = (sourceHeight - cropHeight) / 2;
                uint sourceXFraction = (uint)(cropWidth * FractionValue / TargetWidth);
                uint sourceYFraction = (uint)(cropHeight * FractionValue / TargetHeight);
                byte[] rgb = new byte[TargetWidth * TargetHeight * 3];
                int destinationIndex = 0;
                uint sourceYAccumulator = 0;

                for (int y = 0; y < TargetHeight; ++y) {
                    int sourceY = (int)(sourceYAccumulator >> FractionBits);
                    uint yFraction = sourceYAccumulator & FractionMask;
                    sourceYAccumulator += sourceYFraction;
                    uint sourceXAccumulator = 0;

                    for (int x = 0; x < TargetWidth; ++x) {
                        int sourceX = (int)(sourceXAccumulator >> FractionBits);
                        uint xFraction = sourceXAccumulator & FractionMask;
                        sourceXAccumulator += sourceXFraction;

                        Color p00 = bitmap.GetPixel(cropX + sourceX, cropY + sourceY);
                        Color p10 = bitmap.GetPixel(cropX + sourceX + 1, cropY + sourceY);
                        Color p01 = bitmap.GetPixel(cropX + sourceX, cropY + sourceY + 1);
                        Color p11 = bitmap.GetPixel(cropX + sourceX + 1, cropY + sourceY + 1);

                        rgb[destinationIndex++] = Interpolate(
                            p00.R, p10.R, p01.R, p11.R, xFraction, yFraction);
                        rgb[destinationIndex++] = Interpolate(
                            p00.G, p10.G, p01.G, p11.G, xFraction, yFraction);
                        rgb[destinationIndex++] = Interpolate(
                            p00.B, p10.B, p01.B, p11.B, xFraction, yFraction);
                    }
                }

                return new PreparedImage {
                    Rgb = rgb,
                    SourceWidth = sourceWidth,
                    SourceHeight = sourceHeight,
                    CropX = cropX,
                    CropY = cropY,
                    CropWidth = cropWidth,
                    CropHeight = cropHeight
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

function ConvertTo-EiRgb888 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath
    )

    $resolvedSource = (Resolve-Path -LiteralPath $SourcePath).Path
    return [EiBatch.ImagePreprocessor]::Convert($resolvedSource)
}

function Get-EiCrc32 {
    param(
        [Parameter(Mandatory = $true)]
        [byte[]]$Data
    )

    return [EiBatch.ImagePreprocessor]::Crc32($Data)
}

Export-ModuleMember -Function ConvertTo-EiRgb888, Get-EiCrc32
