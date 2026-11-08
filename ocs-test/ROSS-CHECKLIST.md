# Open CAD Studio: checks for Ross (about 15 minutes)

Aim: is Open CAD Studio (OCS) good enough to replace AutoCAD for editing and plotting RevA/RevB drawings?
Written 08/11/2026. Use a COPY of a real drawing. Never open the archive original.

Setup
- Copy one issued drawing (DWG) to `C:\ocs-test\real\`. Pick one with decimal dimensions (a flange or a hole spacing is ideal).
- Plot the same drawing from AutoCAD to `C:\ocs-test\real\autocad.pdf` with your usual RevA settings.
- Start OCS: double-click `C:\ocs-test\OpenCADStudio-v2026.44-windows-x86_64-portable.exe`.
  If Malwarebytes quarantines it again, restore it (it is signed, VirusTotal 1/67).
- OCS shows two start-up pop-ups the first time (file associations, donation). Close both.
- Commands: type them in the command line at the bottom, as in AutoCAD.

## 1. Opens cleanly
- [ ] File > Open the copy. Does it open without errors?
- [ ] Type `AUDIT`, answer `N` (check only, don't fix). Any errors listed? Write them down.
- [ ] Anything missing or moved compared with AutoCAD (text, hatches, title block, dimensions)? Screenshot differences.

## 2. Dimensions read right
- [ ] Zoom to a dimension with decimals. Same number as in AutoCAD, with the decimal point?
- [ ] Type `LIST`, click the dimension, Enter. Is the measurement what you expect?
- [ ] Arrows and text sit where they do in AutoCAD?

## 3. Rule 5: dimension edit that sticks
Do this on the copy.
- [ ] Type `DIMDISASSOCIATE`, select one dimension, Enter. (Same trick as the AutoCAD fix.)
- [ ] Change that dimension's point or text with `STRETCH` (drag right-to-left, a crossing window over the end point) or `PROPERTIES` (Ctrl+1).
- [ ] Does the number update, or stay old? Note which.
- [ ] Now `SAVEAS` a new file `C:\ocs-test\real\edit-test.dwg`, close it, open it again. Is the change still there?
- [ ] Try the same edit on a dimension without `DIMDISASSOCIATE`. Does it revert, update correctly, or go wrong?

## 4. Rule 6: hatch with STRETCH
- [ ] `STRETCH` a window that crosses a hatched area. Does the hatch move with its boundary, or get left behind?

## 5. Plot like RevA
- [ ] Type `PLOT`. Set: A4, landscape, fit/window and centred, plot style `monochrome.ctb`, lineweights off. Output PDF to `C:\ocs-test\real\ocs.pdf`.
- [ ] Open `ocs.pdf` and `autocad.pdf` side by side at 100% and 400%. Compare:
  - paper size and centring
  - hairlines (zoom in on thin lines; compare thickness)
  - text (same font, same size, same position)
  - hatch spacing and lines
  - dimension arrows
- [ ] Anything different? Screenshot both at the same zoom.

## 6. Hand back
- [ ] Does the saved DWG open in AutoCAD with no warnings? Does it plot the same as before?

## Send back
- A tick or a cross next to each item above, plus short notes.
- Screenshots of anything that looks wrong.
- `autocad.pdf` and `ocs.pdf` (only if the drawing is okay to share; otherwise send crops).

## How to read the result
- Everything ticks: OCS can take over Ross's editing and plotting.
- 3 or 5 fails: keep AutoCAD for the final plot, use OCS for viewing only.
- 1 fails (won't open or loses things): stop. Report which entities.
