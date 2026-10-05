from math import hypot


class ClassroomMapper:
    def update(self, states: dict, width: int, height: int):
        ordered = sorted(states.values(), key=lambda s: ((s.bbox[1] + s.bbox[3]) / 2, (s.bbox[0] + s.bbox[2]) / 2))
        columns = max(1, round(len(ordered) ** 0.5))
        for index, state in enumerate(ordered):
            state.seat_id = f"R{index // columns + 1}-C{index % columns + 1}"
            cx, cy = (state.bbox[0] + state.bbox[2]) / 2, (state.bbox[1] + state.bbox[3]) / 2
            distances = []
            for other in ordered:
                if other.track_id == state.track_id: continue
                ox, oy = (other.bbox[0] + other.bbox[2]) / 2, (other.bbox[1] + other.bbox[3]) / 2
                distances.append((hypot(cx - ox, cy - oy), other.track_id))
            state.neighbor_ids = [track_id for _, track_id in sorted(distances)[:2]]

