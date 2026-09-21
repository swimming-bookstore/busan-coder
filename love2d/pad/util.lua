-- Text helpers used by the chalkboard and talk bubble.
local U = {}

function U.wrap_words(text, width)
  local out = {}
  local rest = (text or ""):gsub("%s+", " "):gsub("^%s+", ""):gsub("%s+$", "")
  while #rest > width do
    local cut = rest:sub(1, width):match(".*() ")
    if not cut or cut < 8 then cut = width else cut = cut - 1 end
    out[#out + 1] = rest:sub(1, cut):gsub("%s+$", "")
    rest = rest:sub(cut + 1):gsub("^%s+", "")
  end
  if rest ~= "" then out[#out + 1] = rest end
  return out
end

function U.wrap_hard(text, width)
  width = math.max(8, width or 48)
  local out = {}
  local rest = tostring(text or "")
  while #rest > width do
    local chunk = rest:sub(1, width)
    local cut = chunk:match(".*()[%s,;:/]")
    if not cut or cut < math.floor(width * 0.45) then cut = width end
    out[#out + 1] = rest:sub(1, cut):gsub("%s+$", "")
    rest = rest:sub(cut + 1):gsub("^%s+", "")
  end
  if rest ~= "" or #out == 0 then out[#out + 1] = rest end
  return out
end

function U.clip_text(s, width)
  s = tostring(s or "")
  if #s <= width then return s end
  if width <= 1 then return s:sub(1, math.max(0, width)) end
  return s:sub(1, width - 1) .. "~"
end

function U.pad_lines(text)
  text = tostring(text or ""):gsub("\r\n", "\n")
  local out = {}
  for line in (text .. "\n"):gmatch("(.-)\n") do
    out[#out + 1] = line
  end
  if #out == 0 then out[1] = "" end
  return out
end

function U.split_word(word, width)
  width = math.max(1, width or 8)
  word = tostring(word or "")
  if #word <= width then return { word } end
  local out = {}
  while #word > width do
    out[#out + 1] = word:sub(1, width)
    word = word:sub(width + 1)
  end
  if word ~= "" then out[#out + 1] = word end
  return out
end

return U
