-- Standalone smoke test (tools/standalone-smoke.py --look X,Y): holds the spectator camera on one cell, e.g. to
-- photograph terrain, water or a resource field. X and Y are filled in by the runner.
WorldLoaded = function()
  Trigger.AfterDelay(DateTime.Seconds(3), function()
    Camera.Position = Map.CenterOfCell(CPos.New(__LOOK_X__, __LOOK_Y__))
  end)
end
