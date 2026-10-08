-- Standalone smoke test (tools/standalone-smoke.py --lua showcase.lua --look X,Y): places the shared vehicles and the
-- economy buildings of both players around one cell and holds the camera there, for a screenshot of the kit art.
-- Multi0 should be an Allied-side faction and Multi1 a Soviet-side one. Use with --map-rules showcase-rules.yaml so
-- the Allied refinery shows its purifier upgrade.
WorldLoaded = function()
  local allied = Player.GetPlayer("Multi0")
  local soviet = Player.GetPlayer("Multi1")
  local cx, cy = __LOOK_X__, __LOOK_Y__
  local function put(owner, type, dx, dy, facing)
    Actor.Create(type, true, { Owner = owner, Location = CPos.New(cx + dx, cy + dy), Facing = facing or Angle.SouthWest })
  end
  Trigger.AfterDelay(DateTime.Seconds(2), function()
    put(allied, "garefn", -6, -2)
    put(soviet, "nanrct", 2, -5)
    put(allied, "amcv", -2, 3)
    put(allied, "cmin", -4, 4)
    put(soviet, "smcv", 2, 3)
    put(soviet, "harv", 4, 2)
    put(soviet, "htk", 0, 5)
    Camera.Position = Map.CenterOfCell(CPos.New(cx, cy))
  end)
end
