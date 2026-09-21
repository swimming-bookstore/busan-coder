local pad = require("pad")
local D = require("draw")
local socket = require("socket")

local W, H = pad.W, pad.H
local demo
local canvas
local composer = ""
local hist = {}
local histI = -1
local draft = ""
local help = "enter send   esc abort/quit   ctrl+n new   ctrl+l login"
local logged_in = false
local fighter_name = "Busan Coder"
local callsign = "BUSAN"
local status_note = "connecting"
local login_poll_t = 0
local status_t = 0
local login_active = false
local agent_url = os.getenv("BUSAN_AGENT") or "http://127.0.0.1:8765/"
local demo_mode = os.getenv("BUSAN_DEMO") == "1"

local cmd_ch, ev_ch, net_thread

local function parse_host_port(url)
  local h, p = (url or ""):match("^https?://([^:/]+):(%d+)")
  if h then return h, tonumber(p) end
  h = (url or ""):match("^https?://([^:/]+)")
  return h or "127.0.0.1", 80
end

local function port_open(host, port)
  local s = socket.tcp()
  if not s then return false end
  s:settimeout(0.25)
  local ok = s:connect(host, port)
  s:close()
  return not not ok
end

local function spawn_fighter(host, port)
  local src = love.filesystem.getSource() or "."
  local ws = src:gsub("[/\\]love2d[/\\]?$", "")
  if ws == src then ws = src .. "/.." end
  local cmd = string.format(
    'cd %q && PYTHONPATH=%q python3 -m fighter --name "Busan Coder" --callsign BUSAN --workspace %q --host %q --port %d --no-browser >/tmp/love-fighter.log 2>&1 &',
    ws, ws, ws, host, port
  )
  os.execute(cmd)
end

local function push(op, extra)
  local msg = extra or {}
  msg.op = op
  cmd_ch:push(msg)
end

local function set_canvas()
  canvas = love.graphics.newCanvas(W, H)
  canvas:setFilter("nearest", "nearest")
end

local function boot_pad()
  demo:clear_live()
  demo.live = true
  demo.callsign = callsign
  demo.caption = fighter_name
  demo.x, demo.y = W / 2, -80
  demo.launch = 0
  demo.linger = 0
end

function love.load(args)
  love.graphics.setDefaultFilter("nearest", "nearest")
  love.keyboard.setKeyRepeat(true)
  set_canvas()
  demo = pad.Demo.new()
  boot_pad()

  for _, a in ipairs(args or {}) do
    if tostring(a):match("^https?://") then
      agent_url = a
    end
  end

  if demo_mode then
    love.mouse.setVisible(false)
    logged_in = true
    status_note = "mouse follow"
    demo.working = true
    demo.linger = 99
    demo.caption = "FOLLOW  ·  mouse"
    demo:launch_from_enter()
    cmd_ch = love.thread.getChannel("agent_cmd")
    ev_ch = love.thread.getChannel("agent_ev")
    return
  end

  local host, port = parse_host_port(agent_url)
  if not port_open(host, port) then
    spawn_fighter(host, port)
    status_note = "starting fighter"
    local deadline = socket.gettime() + 4
    while socket.gettime() < deadline do
      if port_open(host, port) then break end
      socket.sleep(0.15)
    end
  end

  cmd_ch = love.thread.getChannel("agent_cmd")
  ev_ch = love.thread.getChannel("agent_ev")
  net_thread = love.thread.newThread("net.lua")
  net_thread:start()
  push("url", { url = agent_url })
  push("status")
end

function love.quit()
  if cmd_ch then push("quit") end
end

local function new_chat()
  if demo.working then push("abort") end
  push("new")
  hist = {}
  histI = -1
  draft = ""
  composer = ""
  boot_pad()
end

local function begin_login()
  login_active = true
  login_poll_t = 0
  demo:say("opening xAI device login…", "LOGIN")
  demo.caption = "LOGIN  ·  xAI"
  push("login_start")
end

local function send(text)
  text = (text or ""):gsub("^%s+", ""):gsub("%s+$", "")
  if demo.working then return end
  if text == "" then
    if not logged_in then
      begin_login()
    end
    return
  end
  local low = text:lower()
  if low == "login" or low == "/login" then
    composer = ""
    begin_login()
    return
  end
  if low == "new" or low == "/new" then
    composer = ""
    new_chat()
    return
  end
  hist[#hist + 1] = text
  histI = -1
  draft = ""
  composer = ""
  boot_pad()
  demo:launch_from_enter()
  demo.working = true
  demo.pulse = 1
  demo.caption = "GROK  ·  working"
  demo:set_think("")
  demo:say(text, "YOU")
  push("turn", { text = text })
end

local function on_event(ev)
  local event, v = ev.event, ev.data or {}
  if event == "ready" then
    push("status")
  elseif event == "status" then
    logged_in = not not v.logged_in
    if not demo.working then
      if not v.ok then
        status_note = "fighter offline"
        demo.caption = "OFFLINE  ·  start python3 -m fighter"
      elseif logged_in then
        status_note = "ready"
        if demo.caption == "" or demo.caption:find("LOGIN", 1, true) or demo.caption:find("OFFLINE", 1, true) or demo.caption:find("connecting", 1, true) then
          demo.caption = fighter_name
        end
      else
        status_note = "login needed"
        demo.caption = "LOGIN  ·  enter or type login"
      end
    end
  elseif event == "need_login" then
    logged_in = false
    demo.working = false
    begin_login()
  elseif event == "login" then
    local st = v.status or ""
    if st == "start" then
      local code = v.user_code or ""
      local uri = v.verification_uri_complete or v.verification_uri or "https://auth.x.ai"
      demo:say("code " .. code .. "  " .. uri, "LOGIN")
      demo.caption = "LOGIN  ·  " .. code
      login_active = true
      login_poll_t = 0
    elseif st == "done" then
      login_active = false
      logged_in = true
      status_note = "ready"
      demo:say("logged in. send a task.", "LOGIN")
      demo.caption = fighter_name
      push("status")
    elseif st == "pending" then
      -- keep polling
    elseif st == "denied" or st == "expired" or st == "error" then
      login_active = false
      demo:say(v.error or st, "error")
      demo.caption = "LOGIN  ·  failed"
    end
  else
    pad.client.apply(demo, ev, { name = fighter_name, callsign = callsign })
  end
end

local function canvas_mouse()
  local mx, my = love.mouse.getPosition()
  local ww, wh = love.graphics.getDimensions()
  local s = math.min(ww / W, wh / H)
  local ox = (ww - W * s) / 2
  local oy = (wh - H * s) / 2
  return (mx - ox) / s, (my - oy) / s
end

function love.update(dt)
  dt = math.min(0.05, dt)
  if ev_ch then
    while true do
      local ev = ev_ch:pop()
      if not ev then break end
      on_event(ev)
    end
  end
  if demo then
    local mx, my = canvas_mouse()
    if mx >= 0 and mx <= W and my >= 0 and my <= H then
      demo:aim(mx, my)
      if demo_mode then
        demo.working = true
        demo.linger = 99
      end
    end
  end

  if not demo_mode then
    status_t = status_t + dt
    if status_t > 3 and not demo.working then
      status_t = 0
      push("status")
    end
    if login_active then
      login_poll_t = login_poll_t + dt
      if login_poll_t > 2 then
        login_poll_t = 0
        push("login_poll")
      end
    end
  end

  demo:update(dt)
end

local function draw_hud()
  local hudH = 56
  D.rect(0, H - hudH, W, hudH, pad.INK, 0.78)
  D.text(">", 20, H - 38, pad.COIN, 2)
  local shown = composer
  local maxw = math.floor((W - 80) / 16)
  if #shown > maxw then shown = shown:sub(#shown - maxw + 1) end
  D.text(shown, 48, H - 38, pad.CREAM, 2)
  if (demo.blink % 0.9) < 0.55 then
    D.rect(48 + D.textW(shown, 2), H - 40, 3, 22, pad.COIN, 0.95)
  end
  local line = help
  if status_note ~= "" and status_note ~= "ready" then
    line = status_note .. "   " .. help
  end
  D.text(line, 20, H - 16, pad.DIM, 1)
end

function love.draw()
  love.graphics.setCanvas(canvas)
  love.graphics.clear(pad.VOID[1] / 255, pad.VOID[2] / 255, pad.VOID[3] / 255, 1)
  demo:draw()
  draw_hud()
  love.graphics.setCanvas()

  local ww, wh = love.graphics.getDimensions()
  local s = math.min(ww / W, wh / H)
  local ox = (ww - W * s) / 2
  local oy = (wh - H * s) / 2
  love.graphics.setColor(1, 1, 1, 1)
  love.graphics.draw(canvas, ox, oy, 0, s, s)
end

function love.textinput(t)
  if t == "\n" or t == "\r" then return end
  if demo.working then return end
  composer = composer .. t
end

function love.keypressed(key)
  if key == "escape" then
    if demo.working then
      push("abort")
      demo.working = false
      demo.caption = fighter_name
      demo:say("(aborted)", "DIM")
      return
    end
    love.event.quit()
    return
  end
  if key == "return" or key == "kpenter" then
    send(composer)
    return
  end
  if key == "backspace" then
    composer = composer:sub(1, math.max(0, #composer - 1))
    return
  end
  if key == "n" and love.keyboard.isDown("lctrl", "rctrl") then
    new_chat()
    return
  end
  if key == "l" and love.keyboard.isDown("lctrl", "rctrl") then
    begin_login()
    return
  end
  if key == "up" then
    if #hist == 0 then return end
    if histI < 0 then draft = composer end
    histI = histI < 0 and #hist or math.max(1, histI - 1)
    composer = hist[histI]
    return
  end
  if key == "down" then
    if histI < 0 then return end
    histI = histI + 1
    if histI > #hist then
      histI = -1
      composer = draft
    else
      composer = hist[histI]
    end
    return
  end
end

function love.wheelmoved(_, y)
  if demo then demo:wheel(y) end
end
