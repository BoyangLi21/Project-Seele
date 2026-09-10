"""Studio views of the actual R11 mesh, using the established neutral inspection setup."""
from pathlib import Path
source=Path('D:/eva/tools/render_eva_prototype_r08.py').read_text(encoding='utf8')
source=source.replace('artifacts/world_refinement_r08/prototype','artifacts/world_motion_r11/un/body').replace('eva_prototype_r08.blend','eva_un_r11.blend')
exec(compile(source,'render_eva_prototype_r08.py','exec'))
