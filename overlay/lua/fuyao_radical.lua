-- Reuse the compiled radical dictionary without learning component spellings.
local M = {}

local function normalize(code)
  return (code:gsub("'", ""):gsub("([nl])ue", "%1ve"):gsub("([jqxy])u", "%1v"))
end

local function matches_components(codes, input)
  for code in codes:gmatch("%S+") do
    if code:find("'", 1, true) and normalize(code) == input then
      return true
    end
  end
  return false
end

function M.init(env)
  local config = env.engine.schema.config
  env.insert_after = math.max(1, math.min(8, config:get_int("fuyao_radical/insert_after") or 3))
  env.max_candidates = math.max(1, math.min(5, config:get_int("fuyao_radical/max_candidates") or 2))
  env.translator = Component.Translator(env.engine, "", "table_translator@fuyao_radical")
  env.components = ReverseLookup("radical_pinyin")
  env.readings = ReverseLookup("zdict")
end

function M.tags_match(segment, env)
  return segment:has_tag("abc") and not segment:has_tag("radical_lookup")
    and segment.start == 0 and segment._end == #env.engine.context.input
end

local function lookup(env)
  local context = env.engine.context
  local input = context.input
  -- ASVS 2.2.1: only complete lowercase component input enters this lookup.
  if context:get_option("ascii_mode") or context.caret_pos ~= #input
    or #input > 128 or not input:match("^[a-z][a-z']*[a-z]$")
    or input:find("''", 1, true) then
    return {}
  end

  local code = input:gsub("'", "")
  local segment = Segment(0, #code)
  segment.tags = Set({"abc"})
  local translation = env.translator:query(code, segment)
  if not translation then return {} end

  local matches, seen, scanned = {}, {}, 0
  for candidate in translation:iter() do
    scanned = scanned + 1
    if scanned > 128 then break end
    local text = candidate.text
    if candidate._end == #code and utf8.len(text) == 1 and not seen[text]
      and matches_components(env.components:lookup(text), normalize(code)) then
      seen[text] = true
      local readings = {}
      for reading in env.readings:lookup(text):gmatch("%S+") do
        if reading ~= "n/a" then readings[#readings + 1] = reading end
      end
      local comment = #readings > 0 and table.concat(readings, ", ") or "〔拆字〕"
      local point = utf8.codepoint(text)
      matches[#matches + 1] = {
        text = text, comment = comment, has_reading = #readings > 0,
        basic_cjk = point >= 0x4E00 and point <= 0x9FFF, order = scanned,
      }
    end
  end
  -- Equal-frequency extension-block variants precede 骉/驫 in the upstream table.
  -- Prefer readable, annotated standard-block characters in the two inline slots.
  table.sort(matches, function(a, b)
    if a.has_reading ~= b.has_reading then return a.has_reading end
    if a.basic_cjk ~= b.basic_cjk then return a.basic_cjk end
    return a.order < b.order
  end)
  local candidates = {}
  for i = 1, math.min(env.max_candidates, #matches) do
    local item = matches[i]
    -- A plain Candidate has no main-dictionary phrase to memorize.
    candidates[i] = Candidate("fuyao_radical", 0, #input, item.text, item.comment)
  end
  return candidates
end

function M.func(translation, env)
  local radicals = lookup(env)
  if #radicals == 0 then
    for candidate in translation:iter() do yield(candidate) end
    return
  end

  local seen, inserted, count = {}, false, 0
  local function insert_radicals()
    for _, candidate in ipairs(radicals) do
      if not seen[candidate.text] then
        seen[candidate.text] = true
        yield(candidate)
      end
    end
    inserted = true
  end

  for candidate in translation:iter() do
    if not seen[candidate.text] then
      seen[candidate.text] = true
      yield(candidate)
      count = count + 1
      if count == env.insert_after then insert_radicals() end
    end
  end
  if not inserted then insert_radicals() end
end

function M.fini(env)
  env.translator, env.components, env.readings = nil, nil, nil
end

return M
