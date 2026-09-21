-- Shared palette / stage size for the fighter pad.
local T = {
  W = 1280,
  H = 720,
  VOID = {8, 48, 84},
  NAVY = {12, 72, 112},
  SKY_RUST = {248, 152, 56},
  SKY_GO = {80, 216, 248},
  SKY_CPP = {120, 168, 248},
  SKY_PY = {248, 208, 56},
  COIN = {248, 208, 48},
  CYAN = {80, 216, 248},
  PINK = {248, 120, 168},
  CREAM = {252, 236, 200},
  INK = {32, 20, 12},
  GRASS = {72, 200, 88},
  BRICK = {216, 84, 24},
  DIM = {132, 116, 100},
  GUTTER = {36, 24, 16},
  WELL = {18, 12, 10},
  WHITE = {255, 255, 255},
  TERM = {4, 16, 24},
}

T.SKY_BY_LANG = {
  RUST = T.SKY_RUST,
  GO = T.SKY_GO,
  ["C++"] = T.SKY_CPP,
  PYTHON = T.SKY_PY,
  SH = T.SKY_GO,
}

T.TOOL_COL = {
  READ = T.CYAN,
  WRITE = T.GRASS,
  EDIT = T.COIN,
  BASH = T.PINK,
}

T.LANG_BY_EXT = {
  rs = "RUST",
  go = "GO",
  cpp = "C++",
  py = "PYTHON",
  md = "MD",
  json = "JSON",
  html = "HTML",
  sh = "SH",
}

return T
