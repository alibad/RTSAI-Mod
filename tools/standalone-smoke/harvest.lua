-- Standalone smoke test (tools/standalone-smoke.py --lua harvest.lua --look X,Y): gives Multi0 a refinery (with its
-- free harvester) beside the ore field at X,Y and Multi1 a harvester in the field, and holds the camera there, for
-- screenshots of harvesting (the harvest dust overlay) and the ore mine.
WorldLoaded = function()
  local a = Player.GetPlayer("Multi0")
  local b = Player.GetPlayer("Multi1")
  local cx, cy = __LOOK_X__, __LOOK_Y__
  Trigger.AfterDelay(DateTime.Seconds(2), function()
    Actor.Create("garefn", true, { Owner = a, Location = CPos.New(cx - 7, cy + 2) })
    local h = Actor.Create("harv", true, { Owner = b, Location = CPos.New(cx + 3, cy - 2) })
    h.FindResources()
    Camera.Position = Map.CenterOfCell(CPos.New(cx, cy))
  end)
end
