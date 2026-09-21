-- Tiny JSON encode/decode for Lua 5.1 / LÖVE 11.
local json = {}

local function esc(s)
  s = s:gsub("\\", "\\\\")
  s = s:gsub('"', '\\"')
  s = s:gsub("\n", "\\n")
  s = s:gsub("\r", "\\r")
  s = s:gsub("\t", "\\t")
  return s
end

function json.encode(v)
  local t = type(v)
  if t == "nil" then
    return "null"
  elseif t == "boolean" then
    return v and "true" or "false"
  elseif t == "number" then
    return tostring(v)
  elseif t == "string" then
    return '"' .. esc(v) .. '"'
  elseif t == "table" then
    local n = #v
    if n > 0 then
      local parts = {}
      for i = 1, n do
        parts[i] = json.encode(v[i])
      end
      return "[" .. table.concat(parts, ",") .. "]"
    end
    local parts = {}
    for k, val in pairs(v) do
      if type(k) == "string" then
        parts[#parts + 1] = '"' .. esc(k) .. '":' .. json.encode(val)
      end
    end
    return "{" .. table.concat(parts, ",") .. "}"
  end
  return "null"
end

local function skip(s, i)
  while true do
    local c = s:sub(i, i)
    if c == " " or c == "\n" or c == "\r" or c == "\t" then
      i = i + 1
    else
      return i
    end
  end
end

local parse_value

local function parse_string(s, i)
  i = i + 1
  local out = {}
  while i <= #s do
    local c = s:sub(i, i)
    if c == '"' then
      return table.concat(out), i + 1
    elseif c == "\\" then
      local n = s:sub(i + 1, i + 1)
      local map = { n = "\n", r = "\r", t = "\t", ['"'] = '"', ["\\"] = "\\", ["/"] = "/" }
      if n == "u" then
        local hex = s:sub(i + 2, i + 5)
        local cp = tonumber(hex, 16) or 32
        if cp < 128 then
          out[#out + 1] = string.char(cp)
        elseif cp < 2048 then
          out[#out + 1] = string.char(192 + math.floor(cp / 64), 128 + (cp % 64))
        else
          out[#out + 1] = string.char(224 + math.floor(cp / 4096), 128 + math.floor(cp / 64) % 64, 128 + (cp % 64))
        end
        i = i + 6
      else
        out[#out + 1] = map[n] or n
        i = i + 2
      end
    else
      out[#out + 1] = c
      i = i + 1
    end
  end
  return table.concat(out), i
end

local function parse_number(s, i)
  local j = i
  if s:sub(j, j) == "-" then j = j + 1 end
  while s:sub(j, j):match("%d") do j = j + 1 end
  if s:sub(j, j) == "." then
    j = j + 1
    while s:sub(j, j):match("%d") do j = j + 1 end
  end
  if s:sub(j, j):match("[eE]") then
    j = j + 1
    if s:sub(j, j):match("[+-]") then j = j + 1 end
    while s:sub(j, j):match("%d") do j = j + 1 end
  end
  return tonumber(s:sub(i, j - 1)), j
end

local function parse_array(s, i)
  i = skip(s, i + 1)
  local arr = {}
  if s:sub(i, i) == "]" then return arr, i + 1 end
  while i <= #s do
    local v
    v, i = parse_value(s, i)
    arr[#arr + 1] = v
    i = skip(s, i)
    local c = s:sub(i, i)
    if c == "]" then return arr, i + 1 end
    if c ~= "," then return arr, i end
    i = skip(s, i + 1)
  end
  return arr, i
end

local function parse_object(s, i)
  i = skip(s, i + 1)
  local obj = {}
  if s:sub(i, i) == "}" then return obj, i + 1 end
  while i <= #s do
    i = skip(s, i)
    local key
    key, i = parse_string(s, i)
    i = skip(s, i)
    if s:sub(i, i) ~= ":" then return obj, i end
    i = skip(s, i + 1)
    local v
    v, i = parse_value(s, i)
    obj[key] = v
    i = skip(s, i)
    local c = s:sub(i, i)
    if c == "}" then return obj, i + 1 end
    if c ~= "," then return obj, i end
    i = skip(s, i + 1)
  end
  return obj, i
end

parse_value = function(s, i)
  i = skip(s, i)
  local c = s:sub(i, i)
  if c == '"' then
    return parse_string(s, i)
  elseif c == "{" then
    return parse_object(s, i)
  elseif c == "[" then
    return parse_array(s, i)
  elseif c == "t" and s:sub(i, i + 3) == "true" then
    return true, i + 4
  elseif c == "f" and s:sub(i, i + 4) == "false" then
    return false, i + 5
  elseif c == "n" and s:sub(i, i + 3) == "null" then
    return nil, i + 4
  else
    return parse_number(s, i)
  end
end

function json.decode(s)
  if type(s) ~= "string" or s == "" then return nil end
  local ok, v = pcall(parse_value, s, 1)
  if ok then return v end
  return nil
end

return json
