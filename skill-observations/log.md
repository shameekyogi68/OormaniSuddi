# Skill Observation Log

Observations captured during task-oriented work.

**Status key:** OPEN = not yet actioned | ACTIONED (YYYY-MM-DD) = skill updated/created | DECLINED (YYYY-MM-DD) = user decided not to pursue —
resolved statuses always carry their resolution date

---

## 2026-10-15

### Observation 2: A new live night is new copy in the existing overlay system

**Status:** OPEN
**Date:** 2026-10-15
**Session context:** Editor pasted a Yakshagana poster and asked for a new live folder in the same premium design as the existing live screens, including the clips already made.
**Skill:** New skill candidate: live-event-screens
**Type:** internal
**Phase/Area:** live graphics / OBS lower thirds

**Issue:** The channel already has a measured 1920×1080 transparent lower-third system (LIVE pill, round logo, maroon band, gold role, dark name). A new event was at risk of becoming a fresh visual language, or of shrinking three long Kannada names onto one band until the type was too small to read across a room.

**Suggested improvement:** A skill that, given a poster, (1) copies the reusable channel cards into a dated event folder, (2) builds event cards from the poster wording only, (3) refuses type below the live reading size and splits the card instead, (4) adds full-frame before / break / end slates that share the same band, (5) writes the OBS order into a README.

**Principle:** When a broadcast package already exists, a new event is new copy in that package, measured from the existing frames. A name that does not fit at the reading size gets its own card.


### Observation 3: One overlay per moment, not one file per name

**Status:** OPEN
**Date:** 2026-10-15
**Session context:** After a live-event package of about forty lower-thirds, the editor said there were too many images and asked for fewer, optimized screens.
**Skill:** New skill candidate: live-event-screens
**Type:** open-source
**Phase/Area:** broadcast package scope

**Issue:** Splitting every name onto its own card kept the type large and produced a folder an operator will not switch through during a live show. The useful unit is a moment of the night (title, ensemble, cast), not a person.

**Suggested improvement:** In the live-event-screens candidate, cap the package. Put a whole cast on one card, on two rows, and lower type only to a stated floor. Give a name its own card only when that floor still overflows. Copy the reusable channel cards. Do not add a file that will not be switched to.

**Principle:** An operator changes one overlay at a time, so a package is one card per moment. A name gets its own card only after a shared card cannot hold it at the reading floor.


### Observation 4: Overflow becomes time inside the file

**Status:** OPEN
**Date:** 2026-10-15
**Session context:** The editor asked for the live lower thirds to read at full size and to move, after an earlier cut had combined names into small pills to keep the file count down.
**Skill:** New skill candidate: live-event-screens
**Type:** open-source
**Phase/Area:** broadcast package scope

**Issue:** One file per name kept the type large and made a folder an operator will not switch through. Combining names onto one still kept the file count and made the type too small. Both failed the same moment of the show.

**Suggested improvement:** In the live-event-screens candidate, when a moment's names overflow the reading floor, play them as timed beats inside that one overlay. The previous names leave before the next arrive. Do not add a file, and do not go below the floor.

**Principle:** When type has a fixed reading size and an operator switches few files, overflow becomes time inside the file. It does not become another file, and it does not become smaller type.


### Observation 5: Ship the container the show machine opens

**Status:** OPEN
**Date:** 2026-10-15
**Session context:** Transparent lower thirds were delivered as WebM. The editor opened one and it was unsupported.
**Skill:** New skill candidate: live-event-screens
**Type:** open-source
**Phase/Area:** delivery format

**Issue:** A codec kept the alpha plane and stayed small, and a raw decode confirmed the transparency. The operator's player and OBS on macOS do not open that container, so the file was unusable on the night.

**Suggested improvement:** In the live-event-screens candidate, deliver transparent overlays as QuickTime Animation MOV. Prove the file by opening it with the system player, and by sampling a clear pixel and an opaque pixel. A successful raw decode is not delivery.

**Principle:** A transparent video is finished only when the machine that will play it opens the file. An alpha plane that only a separate decoder can see is not a deliverable.


### Observation 6: Modern QuickTime rejects the Animation codec

**Status:** OPEN
**Date:** 2026-10-15
**Session context:** Transparent overlays were redelivered as QuickTime Animation MOV after WebM was rejected. The editor reported those incompatible too.
**Skill:** New skill candidate: live-event-screens
**Type:** open-source
**Phase/Area:** delivery format

**Issue:** The system media stack reported the Animation file not playable and could not decode it. The same stack played an HEVC file tagged hvc1, and a pixel read through that stack showed a clear centre and an opaque band.

**Suggested improvement:** In the live-event-screens candidate, deliver transparent overlays as HEVC with alpha, tag hvc1, written by the platform encoder. Before handing them over, load each file through the system media stack and require it to be playable, with a clear pixel and an opaque pixel. Do not treat QuickTime Animation as universally playable.

**Principle:** "QuickTime movie" is not a codec. Prove the file with the system player. A codec that only a third-party decoder can read will be reported as incompatible.


### Observation 7: A player that is ready is not the document opening

**Status:** OPEN
**Date:** 2026-10-15
**Session context:** QuickTime Player reported that every transparent overlay document could not be opened. A player object built on the same files reported them ready, and a pixel read showed a clear centre and an opaque band.
**Skill:** New skill candidate: live-event-screens
**Type:** open-source
**Phase/Area:** delivery format

**Issue:** The files were HEVC written by ffmpeg. The system player could decode them, and Quick Look made a thumbnail. QuickTime Player still refused the document. Rewriting the same frames with the platform's own movie writer produced a file QuickTime Player opened, closed, and named.

**Suggested improvement:** In the live-event-screens candidate, the handed-over file is written by the platform movie writer, then opened in QuickTime Player and closed. Do not accept a ready player, a thumbnail, or a raw pixel read as proof the document opens.

**Principle:** The test is the application the person double-clicks. A decoder that can read the frames does not mean that application will open the document.


### Observation 8: Channel cards travel with the night's overlays

**Status:** OPEN
**Date:** 2026-10-15
**Session context:** After the cast lower thirds were moving MOV files, the editor asked what 01, 02 and 03 were, then asked for them to be like the others.
**Skill:** New skill candidate: live-event-screens
**Type:** open-source
**Phase/Area:** delivery format

**Issue:** The subscribe card, the phone card and the sponsor card were still pictures beside a folder of moving overlays. The operator had to add them as a different source type.

**Suggested improvement:** In the live-event-screens candidate, the reusable channel cards are rendered in the same transparent MOV, with the same entrance, as the night's lower thirds. Keep each card's own words.

**Principle:** Every overlay the operator switches during a show is the same kind of file. A still parked next to moving overlays is a second system.


### Observation 9: A shared file type is not a shared design

**Status:** OPEN
**Date:** 2026-10-15
**Session context:** Channel cards had been turned into the same moving transparent movie as the cast cards. The editor said they were still a different design, and cutting them in with the others was a problem.
**Skill:** New skill candidate: live-event-screens
**Type:** open-source
**Phase/Area:** a set of overlays that replace one another

**Issue:** The subscribe card, the phone card and the sponsor card moved like the cast cards and used the same movie type, but the settled frame was a different band. Switching from a cast card to one of them changed the shape of the lower third.

**Suggested improvement:** In the live-event-screens candidate, overlays that the operator cuts between must share the band, lockup and pill geometry. Check a settled frame of each against the others before calling the set done. Rebuild only the ones that do not match. Keep each card's own words.

**Principle:** Sources that replace each other have to share the frame they sit in. Matching the file type does not make them one design.


### Observation 10: A sentence is not a row of role pills

**Status:** OPEN
**Date:** 2026-10-15
**Session context:** A subscribe line had been split into four pills, gold then dark, so each half of the sentence sat on its own chip. The editor rejected it.
**Skill:** New skill candidate: live-event-screens
**Type:** open-source
**Phase/Area:** lower-third copy

**Issue:** The gold pill and the dark pill are a label and the thing it names. Putting one clause of a sentence in the gold pill and the next clause in the dark pill reads as two unrelated chips.

**Suggested improvement:** In the live-event-screens candidate, a sentence stays inside one pill. A second pill is only a real name, handle or number that belongs with that sentence.

**Principle:** A pair of pills names something. It does not break a sentence in half.


### Observation 11: A sponsor card shares the shape and keeps its own colour

**Status:** OPEN
**Date:** 2026-10-16
**Session context:** The sponsor lower third had been redrawn in the channel red, with the same gold and dark pills as the cast. The editor said the colour had to stay the sponsor's, and the shapes had to match the other overlays.
**Skill:** New skill candidate: live-event-screens
**Type:** open-source
**Phase/Area:** a set of overlays that replace one another

**Issue:** Matching the band, lockup and capsules was done by also repainting the sponsor in the channel cloth. A cut then looked consistent, and the sponsor stopped looking like the sponsor.

**Suggested improvement:** In the live-event-screens candidate, overlays that replace each other share the rectangle, the lockup and the capsule geometry. A sponsor card keeps that geometry and wears the sponsor's own colours. The paid label stays on the role pill.

**Principle:** Sources that replace each other share the frame they sit in. Sharing that frame does not mean they share a colour. A paid card keeps the colour of the thing it is selling.

### Observation 12: "Upgrade everything to premium" recurs — it needs a fixed audit-then-stills procedure

**Status:** OPEN
**Date:** 2026-11-12
**Session context:** Owner asked for a whole-channel premium upgrade (visual + sound) for the fifth time since August.
**Skill:** New skill candidate: channel-design-review
**Type:** internal
**Phase/Area:** request intake for open-ended quality asks

**Issue:** Each "make it premium / 9 out of 10" request restarts from zero: the agent re-reads rules, re-discovers the approval-first and stills-only preferences from memory, and invents its own scoring. Nothing carries the last review's scores forward, so "better" is never measured against the previous round.

**Suggested improvement:** A skill with fixed steps: contact sheets of every current format, measured audio numbers (LUFS, true peak, LRA against tokens.Limits), a per-format scorecard kept in REVIEWS/ with the previous scores beside it, proposal stills in the scratchpad, then stop for the owner's pick.

**Principle:** A repeated open-ended quality request is a sign the review itself has no stable yardstick; give it one, and keep the last result next to the new one.
