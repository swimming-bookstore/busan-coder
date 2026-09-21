-- LÖVE fighter pad.
--
--     local pad = require("pad")
--     local demo = pad.Demo.new()
--     pad.client.apply(demo, event, { name = "Busan Coder", callsign = "BUSAN" })
--
local demo = require("pad.demo")
local theme = require("pad.theme")
local client = require("pad.client")

return {
  Demo = demo.Demo,
  W = theme.W,
  H = theme.H,
  VOID = theme.VOID,
  CREAM = theme.CREAM,
  COIN = theme.COIN,
  CYAN = theme.CYAN,
  INK = theme.INK,
  DIM = theme.DIM,
  SKY_PY = theme.SKY_PY,
  SKY_GO = theme.SKY_GO,
  theme = theme,
  client = client,
}
