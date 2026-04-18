"""High-score table — demonstrates storage.save_int_list / load_int_list.

Each run tries to load a persisted top-5 scores list, inserts a random new
score, and saves the updated list back. Close the window (or press fire) to
quit — the scores persist to `~/.amipython/high_scores/scores.dat` in preview,
`PROGDIR:scores.dat` on real Amiga hardware.
"""

from amiga import Display, Bitmap, palette, storage, joy, rnd, run, int_to_str

display = Display(320, 200, bitplanes=3)
screen = Bitmap(320, 200, bitplanes=3)

palette.aga(1, 240, 240, 100)
palette.aga(2, 120, 120, 120)

scores: list[int] = []
for i in range(5):
    scores.append(0)

# Populate from disk if the file exists; otherwise the zeroed defaults stay.
storage.load_int_list("scores", scores)

# Simulate a run's final score and insert it in sorted order.
new_score: int = rnd(10000)
inserted: bool = False
for i in range(5):
    if not inserted and new_score > scores[i]:
        # Shift everyone down.
        j: int = 4
        while j > i:
            scores[j] = scores[j - 1]
            j = j - 1
        scores[i] = new_score
        inserted = True

storage.save_int_list("scores", scores)


def update():
    screen.clear()
    screen.print_at(80, 20, "HIGH SCORES", color=1)
    screen.print_at(80, 38, "-----------", color=2)
    for i in range(5):
        screen.print_at(80, 60 + i * 14, int_to_str(i + 1, 2),
                        int_to_str(scores[i], 6), color=1)
    screen.print_at(60, 160, "NEW THIS RUN", int_to_str(new_score, 6), color=1)


display.show(screen)
run(update, until=lambda: joy.button(0))
