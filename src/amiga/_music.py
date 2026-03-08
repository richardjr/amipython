"""Music module — ProTracker MOD playback via pygame.mixer."""


class _MusicModule:
    def __init__(self):
        self._loaded_path = None

    def load(self, path: str) -> None:
        import inspect
        from pathlib import Path

        caller_dir = Path(inspect.stack()[1].filename).parent
        self._loaded_path = str(caller_dir / path)

    def play(self) -> None:
        if self._loaded_path:
            import pygame

            pygame.mixer.init(frequency=44100, size=-16, channels=2)
            pygame.mixer.music.load(self._loaded_path)
            pygame.mixer.music.play(-1)  # loop forever

    def stop(self) -> None:
        import pygame

        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

    def volume(self, vol: int) -> None:
        import pygame

        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(vol / 64.0)


music = _MusicModule()
