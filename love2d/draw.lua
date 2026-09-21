local fontmod = require("font")
local glyph = fontmod.glyph

local M = {}

local function c(rgb, a)
  a = a == nil and 1 or a
  return rgb[1] / 255, rgb[2] / 255, rgb[3] / 255, a
end

function M.clamp(t, a, b)
  a = a or 0
  b = b or 1
  if t < a then return a end
  if t > b then return b end
  return t
end

function M.lerp(a, b, t)
  return a + (b - a) * t
end

function M.mix(c0, c1, t)
  t = M.clamp(t)
  return {
    M.lerp(c0[1], c1[1], t),
    M.lerp(c0[2], c1[2], t),
    M.lerp(c0[3], c1[3], t),
  }
end

function M.rect(x, y, w, h, col, a)
  if not col then return end
  love.graphics.setColor(c(col, a))
  love.graphics.rectangle("fill", x, y, w, h)
end

function M.diamond(cx, cy, r, col, a)
  love.graphics.setColor(c(col, a))
  love.graphics.polygon("fill", cx, cy - r, cx + r * 0.7, cy, cx, cy + r, cx - r * 0.7, cy)
end

function M.glow(cx, cy, r, col, a)
  a = a or 0.22
  for i = 4, 1, -1 do
    local k = i / 4
    love.graphics.setColor(c(col, a * k * k))
    love.graphics.circle("fill", cx, cy, r * k)
  end
end

function M.textW(s, scale)
  scale = scale or 2
  return #(s or "") * 8 * scale
end

function M.text(s, x, y, col, scale, a)
  scale = scale or 2
  s = s or ""
  local ox = x
  for i = 1, #s do
    local bits = glyph(s:sub(i, i))
    for row = 1, 8 do
      local line = bits[row] or 0
      for coln = 0, 7 do
        local bit = math.floor(line / (2 ^ (7 - coln))) % 2
        if bit == 1 then
          M.rect(ox + coln * scale, y + (row - 1) * scale, scale, scale, col, a)
        end
      end
    end
    ox = ox + 8 * scale
  end
  return ox - x
end

function M.ship(cx, cy, facing, scale, pulse, hull, CYAN, CREAM, WHITE, PINK)
  local sx = 11 * scale * (1 + 0.14 * pulse)
  local sy = 14 * scale * (1 - 0.14 * pulse)
  local function put(px, py, w, h, col, a)
    px = px * facing
    M.rect(cx + px - w / 2, cy + py - h / 2, math.max(1, w), math.max(1, h), col, a)
  end
  M.glow(cx, cy, sx * 1.8, hull, 0.22)
  put(0.72 * sx, 0.12 * sy, 0.55 * sx, 0.18 * sy, hull)
  put(-0.72 * sx, 0.12 * sy, 0.55 * sx, 0.18 * sy, hull)
  put(0.55 * sx, 0.08 * sy, 0.22 * sx, 0.1 * sy, CYAN)
  put(-0.55 * sx, 0.08 * sy, 0.22 * sx, 0.1 * sy, CYAN)
  put(0.38 * sx, -0.42 * sy, 0.1 * sx, 0.28 * sy, CREAM)
  put(-0.38 * sx, -0.42 * sy, 0.1 * sx, 0.28 * sy, CREAM)
  put(0, 0.05 * sy, 0.38 * sx, 0.95 * sy, hull)
  put(0, -0.05 * sy, 0.22 * sx, 0.7 * sy, CREAM)
  M.diamond(cx, cy - 0.55 * sy, 0.22 * sy, CYAN)
  M.diamond(cx, cy - 0.08 * sy, 0.16 * sy, WHITE, 0.9)
  put(0.18 * sx, 0.42 * sy, 0.12 * sx, 0.28 * sy, PINK)
  put(-0.18 * sx, 0.42 * sy, 0.12 * sx, 0.28 * sy, PINK)
end

function M.scissor(x, y, w, h, fn)
  love.graphics.setScissor(x, y, w, h)
  fn()
  love.graphics.setScissor()
end

-- Haeundae-ish dusk sea: warm sky, teal water, foam bands.
function M.sea(t, W, H, sky_tint, sky_a)
  local SKY_HIGH = {72, 148, 204}
  local SKY_DUSK = {255, 168, 112}
  local SEA_LITE = {48, 164, 188}
  local SEA_DEEP = {8, 48, 84}
  local FOAM = {200, 236, 236}
  sky_a = sky_a or 0
  local horizon = math.floor(H * 0.38)
  for i = 0, 17 do
    local k = i / 17
    local col = M.mix(SKY_HIGH, SKY_DUSK, k * 0.72)
    if sky_tint and sky_a > 0.01 then
      col = M.mix(col, sky_tint, 0.10 * sky_a)
    end
    M.rect(0, math.floor(horizon * k), W, math.ceil(horizon / 17) + 1, col)
  end
  M.rect(0, horizon - 6, W, 10, M.mix(SKY_DUSK, SEA_LITE, 0.45), 0.85)
  local water_h = H - horizon
  for i = 0, 23 do
    local k = i / 23
    M.rect(0, horizon + math.floor(water_h * k), W, math.ceil(water_h / 23) + 1, M.mix(SEA_LITE, SEA_DEEP, k))
  end
  for i = 0, 7 do
    local y = horizon + 18 + i * 48
    local phase = t * (0.7 + i * 0.05) + i * 1.4
    for x = 0, W, 28 do
      local bob = math.sin(phase + x * 0.018) * 5
      M.rect(x, y + bob, 20, 3, FOAM, 0.14 + 0.10 * ((i + x) % 2))
    end
  end
  for i = 0, 24 do
    local sx = (i * 211 + math.floor(t * 18)) % W
    local sy = horizon + 20 + (i * 47) % math.max(8, H - horizon - 40)
    M.rect(sx, sy, 3, 2, FOAM, 0.22 + 0.18 * (0.5 + 0.5 * math.sin(t * 2.4 + i)))
  end
end

return M
