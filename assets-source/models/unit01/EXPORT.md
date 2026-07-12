# Unit-01 asset state

The active local evaluation model is generated from the downloaded SmOd addon
by `tools/make_smod_model_pack.py`. The source archive and generated resource
pack are Git-ignored and must not be redistributed.

This folder does not contain a `.bbmodel`: that is an explicit production
blocker, not an omission to hide. Before release, obtain the author's written
permission and an editable source (or replace the model with an original,
properly sourced asset). The local conversion adds provisional hand, weapon,
and camera sockets so animation and camera code can use a stable contract;
they remain prototype geometry until reviewed in an editable source tool.

Local regeneration:

```text
python tools/make_smod_model_pack.py
```

Expected output is `run/resourcepacks/eva_real_model/`.
