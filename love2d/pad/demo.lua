local D = require("draw")
local T = require("pad.theme")
local U = require("pad.util")

local W, H = T.W, T.H
local NAVY = T.NAVY
local SKY_GO, SKY_PY = T.SKY_GO, T.SKY_PY
local COIN, CYAN, PINK, CREAM = T.COIN, T.CYAN, T.PINK, T.CREAM
local INK, GRASS, BRICK, DIM = T.INK, T.GRASS, T.BRICK, T.DIM
local GUTTER, WELL, WHITE = T.GUTTER, T.WELL, T.WHITE
local SKY_BY_LANG = T.SKY_BY_LANG

local Demo = {}
Demo.__index = Demo

function Demo.new()
  local self = setmetatable({}, Demo)
  self:reset()
  return self
end

function Demo:reset()
  self.t = 0
  self.x, self.y = 980, 420
  self.mx, self.my = nil, nil
  self.orbit = 0
  self.facing = -1
  self.scale = 3.2
  self.pulse = 0
  self.phase = 0
  self.thoughts = {}
  self.think_q = {}
  self.think_board = {}
  self.think_busy = false
  self.think_lift = 0
  self.think_hold = 0
  self.think_a = 0
  self.think_roll = 0
  self.thinking = ""
  self.thinkEmitted = 0
  self.think_fill = 0
  self.think_nl = false
  self.trail = {}
  self.sky = SKY_PY
  self.sky_a = 0
  self.file = ""
  self.lang = ""
  self.tool = ""
  self.code = {}
  self.shell = {}
  self.shellCmd = ""
  self.shellQ = {}
  self.shellShots = {}
  self.shellBusy = false
  self.shellKey = ""
  self.shellGap = 0
  self.shellCaret = 0
  self.shell_hold = 0
  self.term = {}
  self.term_mode = false
  self.board = {}
  self.follow = true
  self.view_off = 0
  self.caption = ""
  self.box = {72, 136, 1136, 288}
  self.caret = 0
  self.blink = 0
  self.talks = {}
  self.talk_i = 0
  self.talk_until = 0
  self.talk_who = "BUSAN"
  self.scanlines = true
  self.working = false
  self.linger = 0
  self.launch = 0
  self.codeQ = {}
  self.codeShots = {}
  self.codeBusy = false
  self.codeKey = ""
  self.codeGap = 0
  self.code_lift = 0
  self.shell_lift = 0
  self.live = false
  self.editAt = nil
  self.editOldCount = 0
  self.editSpliced = false
  self.editInsert = nil
  self.editDelay = 0
  self.thinkGap = 0
  self.file_hold = 0
  self.pad_dwell = 0
  self.pending_shell = {}
  self.callsign = "BUSAN"
  self:layout_pads()
end

function Demo:layout_pads()
  local x, w = 72, 1136
  local y = 136
  local talk_h, gap = 88, 8
  local hud = 56
  local talk_y = H - hud - gap - talk_h
  local full_h = talk_y - gap - y
  self.box = {x, y, w, full_h}
end

function Demo:wheel(dy)
  local n = self:board_len()
  local rows = self:pad_rows()
  local maxs = math.max(0, n - rows)
  local cur = self.follow and maxs or (self.view_off or 0)
  cur = math.max(0, math.min(maxs, cur - dy))
  self.view_off = cur
  self.follow = cur >= maxs - 0.1
end

function Demo:think_well()
  local bx, by, bw = self.box[1], self.box[2], self.box[3]
  local th = 84
  local wy = math.max(52, by - th - 6)
  th = by - 6 - wy
  return bx + 10, wy, math.max(80, bw - 20), math.max(64, th)
end

function Demo:talk_well()
  local x, w = self.box[1], self.box[3]
  local talk_h, gap, hud = 88, 8, 56
  local ty = H - hud - gap - talk_h
  return x, ty, w, talk_h
end

function Demo:composer_origin()
  -- middle of the HUD composer bar
  return W / 2, H - 28
end

function Demo:stage()
  self:layout_pads()
  local bx, by, bw, bh = unpack(self.box)
  return bx, by, bw, bh
end

function Demo:board_len()
  if #self.board > 0 then return #self.board end
  return math.max(1, #self.code)
end

function Demo:push_head(path, tool)
  local last = self.board[#self.board]
  if last and last.kind == "head" and last.text == (path or self.file) then
    last.tool = tool or last.tool
    return
  end
  self.board[#self.board + 1] = { kind = "head", text = path or self.file or "file", tool = tool or self.tool }
  self.caret = #self.board - 1
  self.follow = true
end


function Demo:muzzle()
  return self.x + self.facing * 18, self.y - 10
end

function Demo:think_width()
  local _, _, ww = self:think_well()
  return math.max(8, math.floor((ww - 24) / 16))
end

function Demo:enqueue_think(word)
  word = tostring(word or "")
  if word == "" then return end
  local width = self:think_width()
  for _, piece in ipairs(U.split_word(word, width)) do
    local fill = self.think_fill or 0
    local force = self.think_nl
    self.think_nl = false
    local join = (not force) and fill > 0 and (fill + 1 + #piece <= width)
    local col = join and (fill + 1) or 0
    self.think_q[#self.think_q + 1] = { text = piece, join = join, col = col }
    self.think_fill = col + #piece
    if #piece >= width then
      self.think_nl = true
      self.think_fill = 0
    end
  end
end

function Demo:fire_next_thought()
  if #self.think_q == 0 then return end
  if (self.thinkGap or 0) > 0 then return end
  local flying = 0
  for _, th in ipairs(self.thoughts) do
    if th.form < 1 then flying = flying + 1 end
  end
  if flying >= 5 then return end
  local item = table.remove(self.think_q, 1)
  if type(item) == "string" then item = { text = item, join = false, col = 0 } end
  local wx, wy, ww, wh = self:think_well()
  local x0, y0 = self:muzzle()
  local hx = wx + 10 + (item.col or 0) * 16
  local hy = wy + wh - 22
  local dx, dy = hx - x0, hy - y0
  local dist = math.sqrt(dx * dx + dy * dy)
  if dist < 1 then dist = 1 end
  local speed = 860
  self.thoughts[#self.thoughts + 1] = {
    x = x0, y = y0, vx = (dx / dist) * speed, vy = (dy / dist) * speed,
    hx = hx, hy = hy, text = item.text, join = item.join, age = 0, life = 2.2, color = CYAN, form = 0,
  }
  self.think_busy = true
  self.thinkGap = 0.03
  if #self.thoughts > 8 then
    local keep = {}
    for i = #self.thoughts - 7, #self.thoughts do keep[#keep + 1] = self.thoughts[i] end
    self.thoughts = keep
  end
end

function Demo:set_pad_file(path, tool)
  path = path or self.file or "file"
  self.file = path:match("([^/\\]+)$") or path
  local ext = (path:match("%.([%w]+)$") or ""):lower()
  local lang = T.LANG_BY_EXT[ext] or "FILE"
  self.lang = lang
  self.sky = SKY_BY_LANG[lang] or self.sky or SKY_PY
  if tool then self.tool = tool end
  if tool and tool ~= "BASH" then
    self.term_mode = false
    self.shell_hold = 0
    self.shellQ = {}
    self.shellShots = {}
    self.shellBusy = false
  end
  self.sky_a = 1
  self.live = true
end

function Demo:pad_rows()
  local bh = self.box[4]
  return math.max(1, math.floor((bh - 56 - 28) / 36))
end

function Demo:pad_cols()
  local bw = self.box[3] or 1136
  return math.max(12, math.floor((bw - 80 - 16) / 16))
end

function Demo:last_shell_run()
  local n = #self.board
  local last = n
  while last >= 1 and self.board[last].kind ~= "shell" do
    last = last - 1
  end
  if last < 1 then return 0, 0 end
  local first = last
  while first > 1 and self.board[first - 1].kind == "shell" do
    first = first - 1
  end
  return first, last
end

function Demo:bash_fill()
  if self.term_mode then return true end
  if self.follow == false then return false end
  return self.tool == "BASH" or self.shellBusy or #self.shellQ > 0 or #self.shellShots > 0 or (self.shell_hold or 0) > 0
end

function Demo:view_start()
  local n = self:board_len()
  local rows = self:pad_rows()
  if self:bash_fill() then
    local first, last = self:last_shell_run()
    local start = math.max(0, first - 1)
    if last - start > rows then start = last - rows end
    return start
  end
  local maxs = math.max(0, n - rows)
  if self.follow ~= false then
    return maxs
  end
  return math.max(0, math.min(maxs, math.floor(self.view_off or 0)))
end


function Demo:load_original(path, text)
  self:set_pad_file(path, self.tool ~= "" and self.tool or "READ")
  self.code = U.pad_lines(text)
  self.codeQ = {}
  self.codeShots = {}
  self.codeBusy = false
  self.editAt = nil
  self.editOldCount = 0
  self.editSpliced = false
  self.editInsert = nil
  self.editDelay = 0
  if #self.board == 0 then
    self:push_head(self.file, "READ")
    for i, line in ipairs(self.code) do
      self.board[#self.board + 1] = { kind = "code", text = line, num = i }
    end
    self.caret = math.max(0, #self.board - 1)
    self.follow = true
  end
end

function Demo:shoot_read(path, text)
  self:set_pad_file(path, "READ")
  local lines = U.pad_lines(text)
  local key = "r\0" .. self.file .. "\0" .. table.concat(lines, "\n")
  if key == self.codeKey then return end
  self.codeKey = key
  self.editAt = nil
  self.editOldCount = 0
  self.editSpliced = false
  self.editInsert = nil
  self.editDelay = 0
  self.code = {}
  self:push_head(self.file, "READ")
  self.codeQ = lines
  self.codeShots = {}
  self.codeBusy = false
  self.pad_dwell = math.max(self.pad_dwell or 0, 1.8)
end

function Demo:shoot_write(path, text)
  self:set_pad_file(path, "WRITE")
  local lines = U.pad_lines(text)
  local key = "w\0" .. self.file .. "\0" .. table.concat(lines, "\n")
  if key == self.codeKey then return end
  self.codeKey = key
  self.editAt = nil
  self.editOldCount = 0
  self.editSpliced = false
  self.editInsert = nil
  self.editDelay = 0
  self.code = {}
  self:push_head(self.file, "WRITE")
  self.codeQ = lines
  self.codeShots = {}
  self.codeBusy = false
  self.pad_dwell = math.max(self.pad_dwell or 0, 2.6)
end

function Demo:shell_cols()
  local bw = self.box[3] or 1136
  return math.max(12, math.floor((bw - 24) / 16))
end

function Demo:enter_bash(cmd)
  self.tool = "BASH"
  self.sky = SKY_GO
  self.sky_a = 1
  self.shellCmd = (cmd ~= "" and cmd) or "bash"
  self.term = {}
  self.term_mode = true
  self.shell_hold = 4.5
  self.file_hold = 0
  self.follow = true
  self.editDelay = 0
  self.codeQ = {}
  self.codeShots = {}
  self.codeBusy = false
  self.code_lift = 0
  self:layout_pads()
  self.live = true
end

function Demo:code_inflight()
  return self.codeBusy or #self.codeQ > 0 or #self.codeShots > 0 or (self.editDelay or 0) > 0
end

function Demo:shoot_shell(cmd, text)
  cmd = tostring(cmd or ""):gsub("%s+", " "):gsub("^%s+", ""):gsub("%s+$", "")
  local cols = self:shell_cols()
  local lines = {}
  if cmd ~= "" then
    for i, row in ipairs(U.wrap_hard(cmd, cols - 2)) do
      lines[#lines + 1] = (i == 1 and "$ " or "  ") .. row
    end
  end
  for _, row in ipairs(U.pad_lines(text)) do
    for _, w in ipairs(U.wrap_hard(row, cols)) do
      lines[#lines + 1] = w
    end
  end
  local key = "sh\0" .. cmd .. "\0" .. table.concat(lines, "\n")
  if key == self.shellKey then return end
  self.shellKey = key
  self.pending_shell = self.pending_shell or {}
  self.pending_shell[#self.pending_shell + 1] = { cmd = cmd, lines = lines }
end

function Demo:maybe_start_shell()
  if not self.pending_shell or #self.pending_shell == 0 then return end
  if self:code_inflight() then return end
  if (self.pad_dwell or 0) > 0 then return end
  if self.shellBusy or #self.shellQ > 0 or #self.shellShots > 0 then return end
  local job = table.remove(self.pending_shell, 1)
  self:enter_bash(job.cmd)
  self.shellQ = job.lines
  self.shellShots = {}
  self.shellBusy = #job.lines > 0
end

local function find_old(code_lines, old_text)
  local old_lines = U.pad_lines(old_text)
  if #old_lines == 0 then return 0 end
  for i = 1, #code_lines - #old_lines + 1 do
    local ok = true
    for j = 1, #old_lines do
      if code_lines[i + j - 1] ~= old_lines[j] then
        ok = false
        break
      end
    end
    if ok then return i - 1 end
  end
  local joined = table.concat(code_lines, "\n")
  local idx = joined:find(old_text, 1, true)
  if idx then
    return #U.pad_lines(joined:sub(1, idx - 1)) - 1
  end
  return 0
end

function Demo:shoot_edit(path, old_text, new_text)
  self:set_pad_file(path, "EDIT")
  if #self.code == 0 then self:load_original(path, "") end
  local start = find_old(self.code, old_text)
  local new_lines = U.pad_lines(new_text)
  local key = "e\0" .. self.file .. "\0" .. tostring(start) .. "\0" .. table.concat(new_lines, "\n")
  if key == self.codeKey then return end
  self.codeKey = key
  self.editAt = start
  self.editOldCount = math.max(1, #U.pad_lines(old_text))
  self.editSpliced = false
  self.editInsert = start
  self:push_head(self.file, "EDIT")
  self.codeQ = new_lines
  self.codeShots = {}
  self.codeBusy = false
  self.editDelay = 0.35
  self.pad_dwell = math.max(self.pad_dwell or 0, 2.2)
end

function Demo:code_target()
  local bx, by = self.box[1], self.box[2]
  local i = #self.board
  local vis = i - self:view_start()
  return bx + 80, by + 56 + vis * 36
end

function Demo:nudge_code_scroll()
  if self:board_len() > self:pad_rows() then
    self.code_lift = 36
  end
  if (self.file_hold or 0) <= 0 then
    self.follow = true
  end
end

function Demo:file_head_index()
  for i = #self.board, 1, -1 do
    local r = self.board[i]
    if r.kind == "head" and r.tool ~= "BASH" then
      return i
    end
  end
  return 1
end

function Demo:pin_last_file()
  local head = self:file_head_index()
  local start = math.max(0, head - 1)
  local rows = self:pad_rows()
  local maxs = math.max(0, self:board_len() - rows)
  if start > maxs then start = maxs end
  self.view_off = start
  self.follow = false
  self.file_hold = 8.5
end

function Demo:nudge_shell_scroll()
  self:nudge_code_scroll()
end

function Demo:apply_code_line(text)
  if self.editAt ~= nil then
    if not self.editSpliced then
      for _ = 1, self.editOldCount do
        if self.editAt + 1 <= #self.code then
          table.remove(self.code, self.editAt + 1)
        end
      end
      self.editSpliced = true
      self.editInsert = self.editAt
    end
    table.insert(self.code, self.editInsert + 1, text)
    self.editInsert = self.editInsert + 1
  else
    self.code[#self.code + 1] = text
  end
  self.board[#self.board + 1] = { kind = "code", text = text, num = #self.code }
  self.caret = math.max(0, #self.board - 1)
  self:nudge_code_scroll()
  self.pulse = 1
end

function Demo:code_fast()
  return self.tool == "READ" or self.tool == "WRITE"
end

function Demo:shell_line_xy(row)
  local bx, by = self.box[1], self.box[2]
  local lift = self.code_lift or 0
  local rows = self:pad_rows()
  local n = #self.term
  local start = math.max(0, n - rows)
  local r = (row or 0) - start
  if r < 0 then r = 0 end
  if r > rows - 1 then r = rows - 1 end
  return bx + 16, by + 56 + r * 36 + lift
end

function Demo:apply_shell_line(text)
  self.term[#self.term + 1] = text
  self.shell[#self.shell + 1] = text
  self.board[#self.board + 1] = { kind = "shell", text = text }
  self.shellCaret = math.max(0, #self.term - 1)
  self.caret = self.shellCaret
  if #self.term > self:pad_rows() then
    self.code_lift = 36
  end
  self.pulse = 1
end

function Demo:fire_next_shell()
  if not self.term_mode then return end
  if #self.shellQ == 0 then return end
  self.tool = "BASH"
  self.sky = SKY_GO
  self.sky_a = 1
  if (self.shellGap or 0) > 0 then return end
  local flying = 0
  for _, sh in ipairs(self.shellShots) do
    if sh.form < 1 then flying = flying + 1 end
  end
  if flying >= 2 then return end
  local line = table.remove(self.shellQ, 1)
  local dest = #self.term
  for _, sh in ipairs(self.shellShots) do
    if sh.form < 1 then dest = dest + 1 end
  end
  local hx, hy = self:shell_line_xy(dest)
  local x0, y0 = self:muzzle()
  local dx, dy = hx - x0, hy - y0
  local dist = math.sqrt(dx * dx + dy * dy)
  if dist < 1 then dist = 1 end
  local speed = 980
  self.shellShots[#self.shellShots + 1] = {
    x = x0, y = y0, vx = (dx / dist) * speed, vy = (dy / dist) * speed,
    hx = hx, hy = hy, dest = dest, text = line, age = 0, life = 2.8, form = 0,
  }
  self.shellBusy = true
  self.shellGap = 0.09
  if #self.shellShots > 8 then
    local keep = {}
    for i = #self.shellShots - 7, #self.shellShots do keep[#keep + 1] = self.shellShots[i] end
    self.shellShots = keep
  end
end

function Demo:step_shell(dt)
  self.shellGap = math.max(0, (self.shellGap or 0) - dt)
  self:fire_next_shell()
  local live = {}
  for _, sh in ipairs(self.shellShots) do
    sh.age = sh.age + dt
    if sh.dest then
      sh.hx, sh.hy = self:shell_line_xy(sh.dest)
    end
    local dx, dy = sh.hx - sh.x, sh.hy - sh.y
    local dist = math.sqrt(dx * dx + dy * dy)
    local toward = sh.vx * dx + sh.vy * dy
    if dist < 22 or (sh.age > 0.08 and toward <= 0) or sh.age >= sh.life then
      self:apply_shell_line(sh.text)
      sh.form = 1
      sh.x, sh.y = sh.hx, sh.hy
      sh.vx, sh.vy = 0, 0
    else
      local k = 1 - math.exp(-10 * dt)
      local speed = 980
      local inv = 1 / (dist < 1 and 1 or dist)
      sh.vx = sh.vx + (dx * inv * speed - sh.vx) * k
      sh.vy = sh.vy + (dy * inv * speed - sh.vy) * k
      sh.x = sh.x + sh.vx * dt
      sh.y = sh.y + sh.vy * dt
      sh.form = math.min(0.9, 1 - dist / 180)
      live[#live + 1] = sh
    end
  end
  self.shellShots = live
  self.shellBusy = #self.shellShots > 0 or #self.shellQ > 0
  if self.shellBusy then
    self.shell_hold = 2.4
    self.term_mode = true
  else
    self.shell_hold = math.max(0, (self.shell_hold or 0) - dt)
    if self.shell_hold <= 0 then
      self.term_mode = false
    end
  end
end

function Demo:code_speed()
  return self:code_fast() and 980 or 820
end

function Demo:fire_next_code()
  if (self.editDelay or 0) > 0 or #self.codeQ == 0 then return end
  if (self.codeGap or 0) > 0 then return end
  local flying = 0
  for _, sh in ipairs(self.codeShots) do
    if sh.form < 1 then flying = flying + 1 end
  end
  local max_fly = self:code_fast() and 2 or 1
  if flying >= max_fly then return end
  local line = table.remove(self.codeQ, 1)
  local hx, hy = self:code_target()
  local x0, y0 = self:muzzle()
  local dx, dy = hx - x0, hy - y0
  local dist = math.sqrt(dx * dx + dy * dy)
  if dist < 1 then dist = 1 end
  local speed = self:code_speed()
  self.codeShots[#self.codeShots + 1] = {
    x = x0, y = y0, vx = (dx / dist) * speed, vy = (dy / dist) * speed,
    hx = hx, hy = hy, text = line, age = 0, life = 2.8, form = 0,
  }
  self.codeBusy = true
  self.codeGap = self:code_fast() and 0.09 or 0.16
  if #self.codeShots > 8 then
    local keep = {}
    for i = #self.codeShots - 7, #self.codeShots do keep[#keep + 1] = self.codeShots[i] end
    self.codeShots = keep
  end
end

function Demo:step_code(dt)
  if (self.editDelay or 0) > 0 then
    self.editDelay = math.max(0, self.editDelay - dt)
  end
  self.codeGap = math.max(0, (self.codeGap or 0) - dt)
  self:fire_next_code()
  local live = {}
  for _, sh in ipairs(self.codeShots) do
    sh.age = sh.age + dt
    local dx, dy = sh.hx - sh.x, sh.hy - sh.y
    local dist = math.sqrt(dx * dx + dy * dy)
    local toward = sh.vx * dx + sh.vy * dy
    if dist < 36 or (sh.age > 0.05 and toward <= 0) or sh.age >= sh.life then
      self:apply_code_line(sh.text)
      sh.form = 1
      sh.x, sh.y = sh.hx, sh.hy
      sh.vx, sh.vy = 0, 0
    else
      local k = 1 - math.exp(-10 * dt)
      local speed = self:code_speed()
      local inv = 1 / (dist < 1 and 1 or dist)
      sh.vx = sh.vx + (dx * inv * speed - sh.vx) * k
      sh.vy = sh.vy + (dy * inv * speed - sh.vy) * k
      sh.x = sh.x + sh.vx * dt
      sh.y = sh.y + sh.vy * dt
      sh.form = math.min(0.9, 1 - dist / 180)
      live[#live + 1] = sh
    end
  end
  self.codeShots = live
  local busy = #self.codeShots > 0 or #self.codeQ > 0
  if self.codeBusy and not busy then
    self:pin_last_file()
    self.pad_dwell = math.max(self.pad_dwell or 0, 2.4)
  end
  self.codeBusy = busy
end

function Demo:flush_think(done)
  local raw = self.thinking or ""
  local emitted = self.thinkEmitted or 0
  if emitted > #raw then emitted = 0 end
  local extra = raw:sub(emitted + 1)
  local width = self:think_width()
  extra = extra:gsub("\r\n", "\n"):gsub("\r", "\n")
  local i = 1
  while i <= #extra do
    local nl = extra:find("\n", i, true)
    local piece = extra:sub(i, (nl and nl - 1) or #extra)
    local words = {}
    for w in piece:gmatch("%S+") do words[#words + 1] = w end
    local last_word = #words > 0 and words[#words] or ""
    local hold = (not done and not nl) and last_word or ""
    local n = #words
    if hold ~= "" then n = n - 1 end
    for k = 1, n do self:enqueue_think(words[k]) end
    if nl then
      self.think_nl = true
      self.think_fill = 0
      i = nl + 1
    else
      self.thinkEmitted = #raw - #hold
      return
    end
  end
  if extra:sub(-1) == "\n" then
    self.think_nl = true
    self.think_fill = 0
  end
  self.thinkEmitted = #raw
end

function Demo:set_think(text, done)
  local nxt = text or ""
  local prev = self.thinking or ""
  if nxt == "" or nxt:sub(1, #prev) ~= prev then
    self.think_q = {}
    self.thinkEmitted = 0
    self.think_fill = 0
    self.think_nl = false
    self.thoughts = {}
    self.think_board = {}
    self.think_busy = false
  end
  self.thinking = nxt
  if nxt ~= "" then
    self.think_hold = 3.4
  end
  self:flush_think(not not done)
end

function Demo:launch_from_enter()
  local cx, cy = self:composer_origin()
  self.x, self.y = cx, cy
  self.launch_x, self.launch_y = cx, cy
  self.facing = 1
  self.pulse = 1
  self.trail = {}
  self.launch = 1
  self.launch_t = 0
  self.linger = 3.2
  self.live = true
end

function Demo:clear_live()
  self.file = ""
  self.lang = ""
  self.code = {}
  self.caret = -1
  self.sky_a = 0
  self.tool = ""
  self.pulse = 0
  self.caption = ""
  self.talks = {}
  self.talk_i = 0
  self.thinking = ""
  self.think_q = {}
  self.thoughts = {}
  self.think_board = {}
  self.thinkEmitted = 0
  self.think_fill = 0
  self.think_nl = false
  self.think_busy = false
  self.think_lift = 0
  self.think_hold = 0
  self.think_a = 0
  self.think_roll = 0
  self.trail = {}
  self.codeQ = {}
  self.codeShots = {}
  self.codeBusy = false
  self.codeKey = ""
  self.code_lift = 0
  self.shell_lift = 0
  self.shell = {}
  self.shellCmd = ""
  self.shellQ = {}
  self.shellShots = {}
  self.shellBusy = false
  self.shellKey = ""
  self.shellCaret = 0
  self.shell_hold = 0
  self.term = {}
  self.term_mode = false
  self.board = {}
  self.follow = true
  self.view_off = 0
  self.editAt = nil
  self.editOldCount = 0
  self.editSpliced = false
  self.editInsert = nil
  self.editDelay = 0
  self.file_hold = 0
  self.linger = 0
  self.launch = 0
  self.working = false
end

function Demo:say(text, who)
  self.talk_who = (who or "BUSAN"):upper()
  text = tostring(text or "")
  self.talks = { text }
  self.talk_i = 0
  self.talk_until = self.t + 1.6 + math.min(2.4, 0.04 * #text)
  self.caption = "SAY  ·  " .. self.talk_who:lower()
end

function Demo:aim(mx, my)
  self.mx, self.my = mx, my
end

function Demo:mouse_hold()
  -- orbit a bit off the pointer so the ship tracks heading, not the cursor
  local mx, my = self.mx, self.my
  if not mx or not my then return nil end
  self.orbit = (self.orbit or 0)
  local ox = math.cos(self.orbit) * 128
  local oy = math.sin(self.orbit * 0.72 + 0.6) * 86
  local tx, ty = mx + ox, my + oy
  local dx, dy = tx - mx, ty - my
  local d = math.sqrt(dx * dx + dy * dy)
  local stand = 140
  if d < stand then
    local s = stand / math.max(d, 1)
    tx = mx + dx * s
    ty = my + dy * s
  end
  local bx, by, bw, bh = self:stage()
  local m = 56
  tx = math.max(bx + m, math.min(bx + bw - m, tx))
  ty = math.max(by + m, math.min(by + bh - m, ty))
  return tx, ty
end

function Demo:update(dt)
  self:layout_pads()
  self.t = self.t + dt
  self.blink = self.blink + dt
  self.pulse = self.pulse * math.exp(-7 * dt)
  self.sky_a = math.max(0, self.sky_a - dt / 1.6)
  self.trail[#self.trail + 1] = {self.x, self.y}
  if #self.trail > 22 then table.remove(self.trail, 1) end

  if (self.file_hold or 0) > 0 then
    self.file_hold = math.max(0, self.file_hold - dt)
    if self.file_hold == 0 then self.follow = true end
  end
  if (self.pad_dwell or 0) > 0 and not self:code_inflight() then
    self.pad_dwell = math.max(0, self.pad_dwell - dt)
  end
  self:step_code(dt)
  self:maybe_start_shell()
  self:step_shell(dt)
  self.code_lift = (self.code_lift or 0) * math.exp(-9 * dt)
  if (self.code_lift or 0) < 0.4 then self.code_lift = 0 end
  self.shell_lift = (self.shell_lift or 0) * math.exp(-9 * dt)
  if (self.shell_lift or 0) < 0.4 then self.shell_lift = 0 end
  self.thinkGap = math.max(0, (self.thinkGap or 0) - dt)
  self:fire_next_thought()
  self.think_lift = self.think_lift + (0 - self.think_lift) * (1 - math.exp(-9 * dt))
  local busy = self.working or self.codeBusy or self.shellBusy or #self.codeQ > 0 or #self.shellQ > 0 or #self.think_q > 0 or #self.thoughts > 0
  if busy then
    self.linger = 3.2
  elseif (self.linger or 0) > 0 then
    self.linger = math.max(0, self.linger - dt)
  end
  if self.live then
    -- live agent: follow mouse heading (standoff) while on stage, else park off-screen
    do
      local bx, by, bw, bh = self:stage()
      local cx, cy = bx + bw / 2, by + bh / 2
      if self.launch and self.launch ~= 0 then
        -- takeoff from composer middle, then mouse follow
        self.launch_t = (self.launch_t or 0) + dt
        local dur = 1.6
        local u = self.launch_t / dur
        if u >= 1 then
          u = 1
          self.launch = 0
        end
        local e = u * u * (3 - 2 * u)
        local x0, y0 = self.launch_x or self.x, self.launch_y or self.y
        local mx, my = W / 2, y0 - 180
        local ox = self.x
        self.x = (1 - e) * (1 - e) * x0 + 2 * (1 - e) * e * mx + e * e * cx
        self.y = (1 - e) * (1 - e) * y0 + 2 * (1 - e) * e * my + e * e * cy
        local vx = dt > 0 and (self.x - ox) / dt or 0
        if vx < -18 then
          self.facing = -1
        elseif vx > 18 then
          self.facing = 1
        end
      else
        local stay = self.working or self.codeBusy or self.shellBusy or #self.codeQ > 0 or #self.shellQ > 0 or #self.think_q > 0 or #self.thoughts > 0 or (self.linger or 0) > 0
        local tx, ty
        if stay then
          self.phase = self.phase + dt
          self.orbit = (self.orbit or 0) + dt * 1.15
          local hx, hy = self:mouse_hold()
          if hx then
            local drift_x = math.sin(self.phase / 3.4 * math.pi * 2) * 36
            local drift_y = math.cos(self.phase / 2.6 * math.pi * 2) * 24
            tx, ty = hx + drift_x, hy + drift_y
          else
            tx = cx + (bw / 2 - 160) * math.sin(self.phase / 5.5 * math.pi * 2)
            ty = cy + (bh / 2 - 140) * math.sin(self.phase / 3.8 * math.pi * 2 + 1.1)
          end
        else
          tx, ty = W / 2, -90
        end
        local k = stay and (1 - math.exp(-3.2 * dt)) or (1 - math.exp(-5.5 * dt))
        local ox = self.x
        self.x = self.x + (tx - self.x) * k
        self.y = self.y + (ty - self.y) * k
        local vx = dt > 0 and (self.x - ox) / dt or 0
        if self.mx and math.abs(self.mx - self.x) > 18 then
          self.facing = self.mx < self.x and -1 or 1
        elseif vx < -28 then
          self.facing = -1
        elseif vx > 28 then
          self.facing = 1
        end
      end
    end
  end
  local live_t = {}
  for _, th in ipairs(self.thoughts) do
    th.age = th.age + dt
    local dx, dy = th.hx - th.x, th.hy - th.y
    local dist = math.sqrt(dx * dx + dy * dy)
    if dist < 22 then
      th.form = 1
      th.x, th.y = th.hx, th.hy
      th.vx, th.vy = 0, 0
      local last = self.think_board[#self.think_board]
      local width = self:think_width()
      if th.join and last and #(last .. " " .. th.text) <= width then
        self.think_board[#self.think_board] = last .. " " .. th.text
      else
        self.think_board[#self.think_board + 1] = U.clip_text(th.text, width)
        self.think_lift = 10
      end
      if #self.think_board > 6 then table.remove(self.think_board, 1) end
      self.think_busy = false
    else
      local k = 1 - math.exp(-14 * dt)
      local speed = 860
      local inv = 1 / (dist < 1 and 1 or dist)
      th.vx = th.vx + (dx * inv * speed - th.vx) * k
      th.vy = th.vy + (dy * inv * speed - th.vy) * k
      th.x = th.x + th.vx * dt
      th.y = th.y + th.vy * dt
      th.form = math.min(1, 1 - dist / 160)
      if th.age < th.life then live_t[#live_t + 1] = th end
    end
  end
  self.thoughts = live_t
  self.think_busy = false
  for _, th in ipairs(self.thoughts) do
    if th.form < 1 then self.think_busy = true break end
  end
  local busy = #self.think_q > 0 or #self.thoughts > 0 or self.think_busy
  if busy then
    self.think_hold = 2.8
  else
    self.think_hold = math.max(0, self.think_hold - dt)
  end
  local want = (busy or self.think_hold > 0) and 1 or 0
  self.think_a = (self.think_a or 0) + (want - (self.think_a or 0)) * (1 - math.exp(-7 * dt))
  self.think_roll = self.think_a
  if self.think_a < 0.02 and want == 0 and not self.working then
    self.think_a = 0
    self.think_roll = 0
    self.thinking = ""
    self.think_board = {}
  end
  if #self.talks > 0 and self.t >= self.talk_until then
    if self.talk_i + 1 < #self.talks then
      self.talk_i = self.talk_i + 1
      local page = self.talks[self.talk_i + 1]
      self.talk_until = self.t + 1.4 + math.min(2.2, 0.04 * #page)
    end
  end
end

function Demo:shell_tint(line)
  if line:sub(1, 2) == "$ " then return COIN end
  if line:find("Error", 1, true) or line:find("error", 1, true) or line:find("Assertion", 1, true) then
    return BRICK
  end
  if line:find("ok", 1, true) or line:find("Hi", 1, true) or line:find("hi", 1, true) then
    return GRASS
  end
  return CREAM
end

function Demo:tint(line, i)
  if self.tool == "READ" and i == 0 then return CYAN end
  if line:find("hello", 1, true) or line:find("print", 1, true) or line:find("ok", 1, true) or line:find("return", 1, true) then
    return GRASS
  end
  if line:find("def ", 1, true) or line:find("for ", 1, true) or line:find("if ", 1, true) then
    return PINK
  end
  if i == 0 then return CYAN end
  return CREAM
end

function Demo:draw()
  self:layout_pads()
  D.sea(self.t, W, H, self.sky, self.sky_a)

  local bx, by, bw, bh = unpack(self.box)
  local TERM = T.TERM
  local bash_fill = self:bash_fill()
  D.rect(bx - 10, by - 10, bw + 20, bh + 20, CREAM, 0.92)
  D.rect(bx - 6, by - 6, bw + 12, bh + 12, INK, 1)
  D.rect(bx, by, bw, 40, D.mix(INK, self.sky, 0.22))
  D.rect(bx, by + 40, bw, bh - 40, bash_fill and TERM or WELL)
  local start = self:view_start()
  local vis = self.board[start + 1]
  local tag, title
  if bash_fill or (vis and vis.kind == "shell") then
    tag, title = "BASH", (self.shellCmd ~= "" and self.shellCmd or "bash")
  else
    local file_tag = "FILE"
    for i = #self.board, 1, -1 do
      local r = self.board[i]
      if r.kind == "head" and r.tool and r.tool ~= "BASH" then
        file_tag = r.tool
        break
      end
    end
    if file_tag == "FILE" and self.tool ~= "" and self.tool ~= "BASH" then file_tag = self.tool end
    tag = (self.file ~= "" and file_tag) or (self.lang ~= "" and self.lang or "")
    title = self.file ~= "" and self.file or ""
  end
  local tool_col = T.TOOL_COL[tag] or self.sky
  local tag_w = D.textW(tag, 2)
  local title_cols = math.max(8, math.floor((bw - 32 - tag_w - 24) / 16))
  D.text(U.clip_text(title, title_cols), bx + 16, by + 10, CREAM, 2)
  D.text(tag, bx + bw - tag_w - 16, by + 10, tool_col, 2)

  if (self.think_a or 0) > 0.02 then
    local a = self.think_a
    local wx, wy, ww, wh = self:think_well()
    D.rect(wx - 2, wy - 2, ww + 4, wh + 4, INK, 0.96 * a)
    D.rect(wx, wy, ww, wh, D.mix(NAVY, CYAN, 0.14), 0.96 * a)
    D.rect(wx, wy, ww, 3, CYAN, a)
    D.text("THINKING", wx + 10, wy + 6, CYAN, 2, a)
    local vis = {}
    local n = #self.think_board
    local tstart = math.max(1, n - 3)
    for i = tstart, n do vis[#vis + 1] = self.think_board[i] end
    local lh = 16
    local width = self:think_width()
    local body = wy + 26
    for i, line in ipairs(vis) do
      local yy = body + (i - 1) * lh
      if yy + lh <= wy + wh - 4 then
        D.text(U.clip_text(line, width), wx + 10, yy, CREAM, 2, a)
      end
    end
  end

  local rows = self:pad_rows()
  local lift = self.code_lift or 0
  D.scissor(bx, by + 40, bw, bh - 40, function()
    if bash_fill then
      local n = #self.term
      local tstart = math.max(0, n - rows)
      local from = lift > 0.5 and (tstart - 1) or tstart
      for i = from, tstart + rows do
        if i < 0 then goto tcontinue end
        local r = i - tstart
        local yy = by + 56 + r * 36 + lift
        if yy < by + 40 - 24 or yy > by + bh then goto tcontinue end
        local line = self.term[i + 1]
        if line == nil then goto tcontinue end
        line = U.clip_text(line, self:shell_cols())
        D.rect(bx, yy - 8, bw, 36, TERM, 0.92)
        if line ~= "" then D.text(line, bx + 16, yy, self:shell_tint(line), 2) end
        if i == (self.shellCaret or 0) and (self.blink % 0.9) < 0.55 then
          D.rect(bx + 16 + D.textW(line, 2), yy - 2, 3, 22, COIN, 0.95)
        end
        ::tcontinue::
      end
      return
    end
    local start = self:view_start()
    local first = self.board[start + 1]
    local skip = (first and first.kind == "head") and 1 or 0
    local from = lift > 0.5 and (start - 1) or start
    for i = from, start + rows + skip do
      if i < 0 then goto continue end
      if i == start and skip == 1 then goto continue end
      local r = i - start - skip
      if i < start then r = i - start end
      local yy = by + 56 + r * 36 + lift
      if yy < by + 40 - 24 or yy > by + bh then goto continue end
      local row = self.board[i + 1]
      if not row then
        goto continue
      end
      if row.kind == "head" then
        if row.tool == "BASH" then goto continue end
        local htag = row.tool or ""
        local hcol = T.TOOL_COL[htag] or COIN
        D.rect(bx, yy - 6, bw, 30, D.mix(INK, hcol, 0.22), 0.85)
        D.text(U.clip_text(row.text or "", math.max(8, math.floor((bw - 32 - D.textW(htag, 2)) / 16))), bx + 16, yy, CREAM, 2)
        if htag ~= "" then D.text(htag, bx + bw - D.textW(htag, 2) - 16, yy, hcol, 2) end
      elseif row.kind == "shell" then
        D.rect(bx, yy - 8, bw, 36, TERM, 0.92)
        local line = U.clip_text(row.text or "", self:shell_cols())
        if line ~= "" then D.text(line, bx + 16, yy, self:shell_tint(line), 2) end
        if i == self.caret and (self.blink % 0.9) < 0.55 then
          D.rect(bx + 16 + D.textW(line, 2), yy - 2, 3, 22, COIN, 0.95)
        end
      else
        D.rect(bx, yy - 8, 64, 36, GUTTER, 0.9)
        local num = string.format("%2d", row.num or (i + 1))
        D.text(num, bx + 14, yy, DIM, 2)
        local line = U.clip_text(row.text or "", self:pad_cols())
        if line ~= "" then D.text(line, bx + 80, yy, self:tint(line, (row.num or 1) - 1), 2) end
        if i == self.caret and (self.blink % 0.9) < 0.55 then
          D.rect(bx + 80 + D.textW(line, 2), yy - 2, 3, 22, COIN, 0.95)
        end
      end
      ::continue::
    end
    if #self.board == 0 then
      for r = 0, rows - 1 do
        local yy = by + 56 + r * 36
        D.rect(bx, yy - 8, 64, 36, GUTTER, 0.95)
        D.text(string.format("%2d", r + 1), bx + 14, yy, DIM, 2)
      end
    end
  end)

  D.rect(0, 0, W, 48, INK, 0.72)
  D.text("Busan Coder", 20, 16, COIN, 2)
  local credit = "Inspired by Causewaybay Hacker"
  D.text(credit, W - D.textW(credit, 2) - 20, 16, CREAM, 2)

  for i, p in ipairs(self.trail) do
    local k = i / math.max(1, #self.trail)
    D.diamond(p[1], p[2], 3 + 4 * k, CYAN, 0.12 * k)
  end

  local tool_col = T.TOOL_COL[self.tool] or self.sky or CYAN
  for _, sh in ipairs(self.codeShots) do
    if sh.form < 1 then
      D.diamond(sh.x - 6, sh.y + 8, 8, tool_col, 0.95)
      local bit = (sh.text or " "):sub(1, 28)
      D.text(bit, sh.x + 1, sh.y + 1, INK, 2)
      D.text(bit, sh.x, sh.y, CREAM, 2)
    end
  end

  for _, sh in ipairs(self.shellShots) do
    if sh.form < 1 then
      D.diamond(sh.x - 6, sh.y + 8, 8, PINK, 0.95)
      local bit = (sh.text or " "):sub(1, 22)
      D.text(bit, sh.x + 1, sh.y + 1, INK, 2)
      D.text(bit, sh.x, sh.y, self:shell_tint(sh.text or ""), 2)
    end
  end

  for _, th in ipairs(self.thoughts) do
    if th.form < 1 then
      D.diamond(th.x - 6, th.y + 8, 8, CYAN, 0.95)
      D.text(th.text, th.x + 1, th.y + 1, INK, 2)
      D.text(th.text, th.x, th.y, CYAN, 2)
    end
  end

  if self.scanlines then
    for y = 0, H - 1, 3 do D.rect(0, y, W, 1, INK, 0.10) end
  end

  local open = false
  for _, t in ipairs(self.talks) do
    if t and t:match("%S") then open = true break end
  end
  if open then
    local tx, ty, tw, th = self:talk_well()
    local page = self.talks[self.talk_i + 1] or ""
    D.rect(tx - 2, ty - 2, tw + 4, th + 4, INK, 0.92)
    D.rect(tx, ty, tw, th, CREAM, 0.96)
    D.rect(tx, ty, tw, 4, COIN, 1)
    D.text(self.talk_who or "BUSAN", tx + 10, ty + 8, INK, 2)
    local width = math.max(8, math.floor((tw - 24) / 16))
    local lines = U.wrap_words(page, width)
    local pages = {}
    for i = 1, #lines, 3 do
      pages[#pages + 1] = { lines[i], lines[i + 1], lines[i + 2] }
    end
    if #pages == 0 then pages[1] = { "" } end
    if self.talk_i >= #pages then self.talk_i = #pages - 1 end
    local vis = pages[self.talk_i + 1] or {}
    for i = 1, 3 do
      if vis[i] then D.text(vis[i], tx + 10, ty + 32 + (i - 1) * 18, INK, 2) end
    end
    if #pages > 1 then
      local mark = string.format("%d/%d", self.talk_i + 1, #pages)
      D.text(mark, tx + tw - D.textW(mark, 2) - 10, ty + 8, DIM, 2)
    end
  end

  if self.y > -40 then
    local thrust = 0.7
    for i = 0, 7 do
      local fy = self.y + 28 + i * 5 * thrust
      D.diamond(self.x, fy, 6 - i * 0.45, D.mix(CYAN, COIN, i / 8), 0.55 * thrust)
    end
    local bob = math.sin(self.t * 1.6 * math.pi * 2) * 4
    D.ship(self.x, self.y + bob, self.facing, self.scale, self.pulse, self.sky, CYAN, CREAM, WHITE, PINK)
  end
end

return {
  Demo = Demo,
}
