class PoseEstimator:
    """Optional RTMPose adapter. Detection remains usable when MMPose is not installed."""

    def __init__(self):
        self.inferencer = None
        try:
            from mmpose.apis import MMPoseInferencer
            self.inferencer = MMPoseInferencer("human")
        except (ImportError, RuntimeError):
            pass

    def estimate(self, frame, bbox):
        if self.inferencer is None:
            return []
        x1, y1, x2, y2 = bbox
        crop = frame[max(0, y1):y2, max(0, x1):x2]
        result = next(self.inferencer(crop, return_vis=False))
        predictions = result.get("predictions", [[]])[0]
        return predictions[0].get("keypoints", []) if predictions else []

