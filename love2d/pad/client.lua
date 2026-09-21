-- Talk to python3 -m fighter over the pad HTTP API (SSE turns).
local M = {}

function M.tool_name(v)
  local n = tostring((v and v.name) or "")
  return (n:match("([^%.]+)$") or n):lower()
end

function M.apply(demo, ev, opts)
  opts = opts or {}
  local event, v = ev.event, ev.data or {}
  local callsign = opts.callsign or demo.callsign or "BUSAN"
  local name = opts.name or "Busan Coder"

  if event == "think" then
    demo:set_think((demo.thinking or "") .. (v.text or ""))
    demo.pulse = 0.7
    demo.caption = "THINKING  ·  grok"
  elseif event == "delta" then
    demo._agent = (demo._agent or "") .. (v.text or "")
    demo:say(demo._agent, callsign)
    demo.caption = "SAY  ·  grok"
  elseif event == "open" then
    if (v.name or "") == "edit" and v.path then
      demo.caption = "EDIT  ·  " .. tostring(v.path)
      demo.pulse = 1
      demo:load_original(v.path, v.preview or "")
    end
  elseif event == "tool" then
    local tn = M.tool_name(v)
    demo.caption = "TOOL  ·  " .. tn
    demo.pulse = 1
    if tn == "read" then
      demo:shoot_read(v.path or demo.file, v.preview or v.detail or "")
    elseif tn == "write" and not v.is_error then
      demo:shoot_write(v.path or demo.file, v.preview or v.content or "")
    elseif tn == "edit" and not v.is_error then
      if v.edit_orig or v.preview then
        demo:load_original(v.path or demo.file, v.edit_orig or v.preview or "")
      end
      demo:shoot_edit(v.path or demo.file, v.edit_old or "", v.edit_new or "")
    elseif tn == "bash" then
      demo:shoot_shell(v.cmd or "", v.preview or v.detail or "")
    end
    if v.detail then
      local label = (v.is_error and "error" or "ok") .. "  " .. tostring(v.path or v.cmd or "")
      demo:say(label:gsub("%s+$", ""), tn:upper())
    end
  elseif event == "error" then
    demo:say(v.text or "error", "error")
    demo.working = false
    demo.caption = "ERROR"
  elseif event == "end" then
    if v.text and v.text ~= "" and not demo._agent then
      demo:say(v.text, callsign)
    end
  elseif event == "done" then
    demo:flush_think(true)
    demo.working = false
    demo._agent = nil
    if demo.caption:find("GROK", 1, true) or demo.caption:find("THINKING", 1, true) or demo.caption:find("SAY", 1, true) or demo.caption:find("TOOL", 1, true) then
      demo.caption = name
    end
  end
end

return M
