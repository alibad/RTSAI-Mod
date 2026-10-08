-- Standalone smoke test observer (tools/standalone-smoke.py --observe): pans the spectator camera between the bot
-- bases and logs, every 30 s, how many actors of each type every bot owns. Output goes to lua.log.
WorldLoaded = function()
  local bots = Player.GetPlayers(function(p) return p.IsBot end)
  for _, p in ipairs(bots) do
    print("PLAYER|" .. p.InternalName .. "|" .. p.Faction)
  end

  local function census()
    for _, p in ipairs(bots) do
      local counts, n = {}, 0
      for _, a in ipairs(p.GetActors()) do
        counts[a.Type] = (counts[a.Type] or 0) + 1
        n = n + 1
      end
      local parts = {}
      for k, v in pairs(counts) do parts[#parts + 1] = k .. "=" .. v end
      table.sort(parts)
      print("CENSUS|" .. DateTime.GameTime .. "|" .. p.InternalName .. "|" .. p.Faction .. "|" .. n .. "|" .. table.concat(parts, ","))
    end
    Trigger.AfterDelay(DateTime.Seconds(30), census)
  end

  local idx = 0
  local function pan()
    if #bots > 0 then
      idx = idx % #bots + 1
      Camera.Position = Map.CenterOfCell(bots[idx].HomeLocation)
      print("CAMERA|" .. DateTime.GameTime .. "|" .. bots[idx].InternalName)
    end
    Trigger.AfterDelay(DateTime.Seconds(15), pan)
  end

  Trigger.AfterDelay(1, census)
  Trigger.AfterDelay(DateTime.Seconds(5), pan)
end
