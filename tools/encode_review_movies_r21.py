"""Export the completed native R21 cycle and F2 passenger review."""
import encode_review_movies_r20 as video
def main():
 root=video.ROOT/'artifacts/world_repair_r21';video.OUT=root/'media';video.OUT.mkdir(exist_ok=True)
 factory=sorted((root/'factory').glob('native_cycle_*'))[-1]
 video.main(factory,'f5','R21_EVA_transfer_launch_recovery')
 flights=sorted((root/'transit').glob('native_movie_r21-flight-riding_*'))
 if flights and (root/'native_flight_pass.json').exists():video.main(flights[-1],'flight','R21_NERV_UN_flight',root/'native_flight_pass.json')
if __name__=='__main__':main()
