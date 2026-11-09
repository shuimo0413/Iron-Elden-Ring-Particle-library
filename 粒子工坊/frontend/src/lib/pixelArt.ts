/** 像素画纯函数：标准像素 JSON ↔ 网格、颜色换算、画布绘制。不 import vue、不发请求。 */

/** [R, G, B, A]，每通道 0–255 */
export type Rgba = [number, number, number, number];

/** 标准像素 JSON，与 粒子库/tool/origin_json 一致 */
export type PixelArt = {
  name: string;
  width: number;
  height: number;
  pixels: { x: number; y: number; rgba: Rgba }[];
};

/** height × width 网格；null 表示没有写出的像素（透明） */
export type PixelGrid = (Rgba | null)[][];

/** 颜色的唯一键，用于比较与高亮 */
export function rgbaKey(rgba: Rgba): string {
  return rgba.join(",");
}

/** (R,G,B,A) → #RRGGBBAA */
export function rgbaToHex(rgba: Rgba): string {
  return "#" + rgba.map((channel) => channel.toString(16).padStart(2, "0").toUpperCase()).join("");
}

/** #RRGGBB + alpha → Rgba */
export function hexToRgba(hex: string, alpha = 255): Rgba {
  const value = hex.replace("#", "");
  return [
    parseInt(value.slice(0, 2), 16),
    parseInt(value.slice(2, 4), 16),
    parseInt(value.slice(4, 6), 16),
    alpha,
  ];
}

/** CSS 颜色字符串 */
export function rgbaCss(rgba: Rgba): string {
  return `rgba(${rgba[0]}, ${rgba[1]}, ${rgba[2]}, ${(rgba[3] / 255).toFixed(3)})`;
}

/** 像素 JSON → 网格 */
export function buildGrid(art: PixelArt): PixelGrid {
  const grid: PixelGrid = Array.from({ length: art.height }, () => Array<Rgba | null>(art.width).fill(null));
  for (const pixel of art.pixels) {
    if (pixel.y >= 0 && pixel.y < art.height && pixel.x >= 0 && pixel.x < art.width) {
      grid[pixel.y][pixel.x] = pixel.rgba;
    }
  }
  return grid;
}

/** 网格 → 像素 JSON（跳过 null 与 alpha=0） */
export function gridToArt(name: string, grid: PixelGrid): PixelArt {
  const pixels: PixelArt["pixels"] = [];
  grid.forEach((row, y) =>
    row.forEach((rgba, x) => {
      if (rgba && rgba[3] > 0) pixels.push({ x, y, rgba: [...rgba] as Rgba });
    }),
  );
  return { name, width: grid[0]?.length ?? 0, height: grid.length, pixels };
}

/** 统计像素画用到的颜色，按出现次数降序 */
export function collectColors(art: PixelArt): { rgba: Rgba; count: number }[] {
  const counts = new Map<string, { rgba: Rgba; count: number }>();
  for (const pixel of art.pixels) {
    const key = rgbaKey(pixel.rgba);
    const entry = counts.get(key);
    if (entry) entry.count += 1;
    else counts.set(key, { rgba: pixel.rgba, count: 1 });
  }
  return [...counts.values()].sort((a, b) => b.count - a.count);
}

export type DrawOptions = {
  /** 每个逻辑像素占多少屏幕像素 */
  scale: number;
  /** 棋盘格底表示透明 */
  checker?: boolean;
  /** 放大到一定程度时画像素网格线 */
  gridLines?: boolean;
  /** 只高亮这个颜色，其余变暗 */
  highlightKey?: string | null;
  checkerLight?: string;
  checkerDark?: string;
};

/** 在 2D 画布上绘制网格（画布尺寸需由调用方先设为 width*scale × height*scale） */
export function drawGrid(ctx: CanvasRenderingContext2D, grid: PixelGrid, options: DrawOptions): void {
  const { scale } = options;
  const height = grid.length;
  const width = grid[0]?.length ?? 0;
  ctx.clearRect(0, 0, width * scale, height * scale);

  if (options.checker) {
    // 棋盘格每格至少 4 屏幕像素，避免高倍放大时格子太细
    const cell = Math.max(4, Math.floor(scale / 2));
    const columns = Math.ceil((width * scale) / cell);
    const rows = Math.ceil((height * scale) / cell);
    for (let row = 0; row < rows; row++) {
      for (let column = 0; column < columns; column++) {
        ctx.fillStyle = (row + column) % 2 === 0 ? options.checkerLight ?? "#e8e8e8" : options.checkerDark ?? "#c8c8c8";
        ctx.fillRect(column * cell, row * cell, cell, cell);
      }
    }
  }

  const dim = options.highlightKey != null;
  grid.forEach((row, y) =>
    row.forEach((rgba, x) => {
      if (!rgba || rgba[3] === 0) return;
      ctx.globalAlpha = dim && rgbaKey(rgba) !== options.highlightKey ? 0.15 : 1;
      ctx.fillStyle = rgbaCss(rgba);
      ctx.fillRect(x * scale, y * scale, scale, scale);
    }),
  );
  ctx.globalAlpha = 1;

  if (options.gridLines && scale >= 8) {
    ctx.strokeStyle = "rgba(0, 0, 0, 0.08)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x <= width; x++) {
      ctx.moveTo(x * scale + 0.5, 0);
      ctx.lineTo(x * scale + 0.5, height * scale);
    }
    for (let y = 0; y <= height; y++) {
      ctx.moveTo(0, y * scale + 0.5);
      ctx.lineTo(width * scale, y * scale + 0.5);
    }
    ctx.stroke();
  }
}
