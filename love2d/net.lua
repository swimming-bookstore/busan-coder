-- Background HTTP thread: talks to the fighter pad API (SSE turns).
require("love.thread")
require("love.filesystem")
local src = love.filesystem.getSource()
if src and src ~= "" then
  package.path = src .. "/?.lua;" .. src .. "/?/init.lua;" .. package.path
end
local socket = require("socket")
local json = require("json")

local cmd_ch = love.thread.getChannel("agent_cmd")
local ev_ch = love.thread.getChannel("agent_ev")

local host, port = "127.0.0.1", 8765
local abort_flag = false
local gen = 0

local function emit(event, data)
  ev_ch:push({ event = event, data = data or {} })
end

local function parse_url(url)
  url = url or "http://127.0.0.1:8765/"
  local h, p = url:match("^https?://([^:/]+):(%d+)")
  if h then
    host, port = h, tonumber(p)
    return
  end
  h = url:match("^https?://([^:/]+)")
  if h then
    host, port = h, 80
  end
end

local function connect(timeout)
  local sock, err = socket.tcp()
  if not sock then return nil, err end
  sock:settimeout(timeout or 8)
  local ok, cerr = sock:connect(host, port)
  if not ok then
    sock:close()
    return nil, cerr
  end
  return sock
end

local function read_headers(sock)
  sock:settimeout(15)
  local buf = ""
  while true do
    local chunk, err, partial = sock:receive(1)
    if chunk then
      buf = buf .. chunk
    elseif partial and #partial > 0 then
      buf = buf .. partial
    else
      if err == "timeout" then
        -- keep waiting a bit
      else
        return nil, err or "closed", buf
      end
    end
    if buf:find("\r\n\r\n", 1, true) then
      local head, rest = buf:match("^(.-)\r\n\r\n(.*)$")
      return head, nil, rest or ""
    end
    if #buf > 65536 then return nil, "headers too large", buf end
  end
end

local function status_code(head)
  local code = head and head:match("^HTTP/%d%.%d%s+(%d+)")
  return tonumber(code) or 0
end

local function request(method, path, body, stream_fn)
  local sock, err = connect(stream_fn and 8 or 8)
  if not sock then return nil, err end
  body = body or ""
  local req = table.concat({
    method .. " " .. path .. " HTTP/1.0",
    "Host: " .. host .. ":" .. port,
    "Accept: */*",
    "Connection: close",
  }, "\r\n")
  if body ~= "" then
    req = req
      .. "\r\nContent-Type: application/json; charset=utf-8"
      .. "\r\nContent-Length: "
      .. tostring(#body)
  end
  req = req .. "\r\n\r\n" .. body
  local ok, send_err = sock:send(req)
  if not ok then
    sock:close()
    return nil, send_err
  end
  local head, herr, rest = read_headers(sock)
  if not head then
    sock:close()
    return nil, herr
  end
  local code = status_code(head)
  if stream_fn then
    stream_fn(sock, rest or "", code)
    sock:close()
    return code, ""
  end
  sock:settimeout(20)
  local chunks = { rest or "" }
  while true do
    local chunk, rerr, partial = sock:receive(4096)
    if chunk then
      chunks[#chunks + 1] = chunk
    elseif partial and #partial > 0 then
      chunks[#chunks + 1] = partial
    else
      break
    end
  end
  sock:close()
  return code, table.concat(chunks)
end

local function handle_sse_block(block)
  local event, data = "message", ""
  for line in (block .. "\n"):gmatch("(.-)\n") do
    line = line:gsub("\r$", "")
    if line:sub(1, 6) == "event:" then
      event = line:sub(7):gsub("^%s+", "")
    elseif line:sub(1, 5) == "data:" then
      data = data .. line:sub(6):gsub("^%s+", "")
    end
  end
  if data == "" then return end
  local v = json.decode(data) or { text = data }
  emit(event, v)
end

local function drain_cmd()
  while true do
    local msg = cmd_ch:pop()
    if not msg then return end
    if type(msg) == "table" then
      if msg.op == "url" then
        parse_url(msg.url)
      elseif msg.op == "abort" then
        abort_flag = true
      elseif msg.op == "quit" then
        abort_flag = true
        return "quit"
      else
        -- stash unexpected commands back? ignore during stream except abort
        if msg.op == "turn" then
          -- a new turn while streaming: abort current
          abort_flag = true
          cmd_ch:push(msg)
          return "abort"
        end
      end
    end
  end
end

local function do_turn(text, mygen)
  abort_flag = false
  local payload = json.encode({ text = text })
  local function stream(sock, rest, code)
    if code == 401 then
      emit("error", { text = "not logged in — enter to login" })
      emit("need_login", {})
      return
    end
    if code >= 400 then
      local v = json.decode(rest) or {}
      emit("error", { text = v.error or ("HTTP " .. tostring(code)) })
      return
    end
    local buf = (rest or ""):gsub("\r\n", "\n")
    sock:settimeout(0.2)
    while mygen == gen and not abort_flag do
      if drain_cmd() == "quit" then return end
      if abort_flag or mygen ~= gen then return end
      local chunk, err, partial = sock:receive(2048)
      if chunk then
        buf = buf .. chunk:gsub("\r\n", "\n")
      elseif partial and #partial > 0 then
        buf = buf .. partial:gsub("\r\n", "\n")
      elseif err == "closed" or err == "timeout" then
        if err == "closed" then
          break
        end
      else
        break
      end
      while true do
        local i = buf:find("\n\n", 1, true)
        if not i then break end
        local block = buf:sub(1, i - 1)
        buf = buf:sub(i + 2)
        handle_sse_block(block)
      end
    end
    if #buf > 0 then handle_sse_block(buf) end
  end
  local ok, err = request("POST", "/api/turn", payload, stream)
  if not ok then
    emit("error", { text = tostring(err or "connect failed") })
  end
  if mygen == gen then
    emit("done", {})
  end
end

local function do_status()
  local code, body = request("GET", "/api/status", "")
  if not code then
    emit("status", { ok = false, error = body or "offline", logged_in = false })
    return
  end
  local v = json.decode(body) or {}
  v.ok = code == 200
  v.http = code
  emit("status", v)
end

local function do_login_start()
  local code, body = request("POST", "/api/login/start", "{}")
  local v = json.decode(body) or {}
  if not code or code >= 400 then
    emit("login", { status = "error", error = v.error or body or "login start failed" })
    return
  end
  emit("login", {
    status = "start",
    user_code = v.user_code,
    verification_uri = v.verification_uri,
    verification_uri_complete = v.verification_uri_complete or v.verification_uri,
  })
end

local function do_login_poll()
  local code, body = request("POST", "/api/login/poll", "{}")
  local v = json.decode(body) or {}
  v.status = v.status or (code and code >= 400 and "error" or "pending")
  emit("login", v)
end

emit("ready", {})

while true do
  local msg = cmd_ch:demand()
  if type(msg) ~= "table" then
    -- ignore
  elseif msg.op == "quit" then
    break
  elseif msg.op == "url" then
    parse_url(msg.url)
  elseif msg.op == "status" then
    do_status()
  elseif msg.op == "abort" then
    abort_flag = true
    request("POST", "/api/abort", "{}")
  elseif msg.op == "new" then
    gen = gen + 1
    abort_flag = true
    request("POST", "/api/new", "{}")
    emit("reset", {})
  elseif msg.op == "login_start" then
    do_login_start()
  elseif msg.op == "login_poll" then
    do_login_poll()
  elseif msg.op == "turn" then
    gen = gen + 1
    local mygen = gen
    do_turn(tostring(msg.text or ""), mygen)
  end
end
