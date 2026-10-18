"""Optional Mix stems view; imported by the normal Audio Editor."""
from __future__ import annotations

import secrets
import hashlib
import streamlit as st

from core.stem_mixer import MAX_STEM_BYTES
from core.stem_uploads import DOWNLOADS, render_uploaded_stems


@st.fragment(run_every=60)
def _download_result(owner: str, saved: dict) -> None:
    result = saved['result']
    if not result.get('ok'):
        st.error(result.get('error') or 'Mix failed')
        return
    audio = DOWNLOADS.get(owner, saved.get('token', ''))
    if audio is None:
        st.info('This temporary download expired. Create the mix again.')
        return
    st.success('WAV mix ready · 48 kHz stereo · 24-bit')
    measurement = result['measurement']
    lufs, peak = measurement.get('integrated_lufs'), measurement.get('true_peak_dbtp')
    st.metric('Integrated loudness', f'{lufs:g} LUFS' if lufs is not None else 'Undefined')
    st.metric('True peak', f'{peak:g} dBTP' if peak is not None else 'No signal')
    st.metric('Clipped samples', str(measurement.get('rail_hits', 'Unknown')))
    if measurement.get('effectively_silent'):
        st.info('The mix is silent; integrated LUFS is undefined.')
    st.download_button('Download WAV mix', audio, file_name='stem_mix.wav', mime='audio/wav',
                       key='stem_download')


def render_stem_mixer(project: dict, *, ffmpeg_ready: bool, max_upload_mb: int,
                      ffmpeg_path: str = '') -> None:
    st.caption('Mix two aligned stems from the same song. Both start at 0:00; the longer stem sets the duration.')
    st.caption('Separate WAV/MP3 stems · up to 64 MB and 5 minutes each. Mastering presets remain in Remaster Studio.')
    st.caption('Scratch files are removed after processing. Download within 10 minutes; save the WAV to keep it.')
    owner = st.session_state.setdefault('_stem_mix_owner', secrets.token_urlsafe(32))
    scope = str(project.get('project_id') or project.get('path') or project.get('title') or 'project')
    key_scope = hashlib.sha256(scope.encode()).hexdigest()[:12]
    vocal = st.file_uploader('Vocal stem', type=['wav', 'mp3'], key=f'stem_vocal_{key_scope}')
    music = st.file_uploader('Instrumental stem', type=['wav', 'mp3'], key=f'stem_music_{key_scope}')
    vocal_db = st.slider('Vocal level (dB)', -24.0, 6.0, -6.0, 0.5, key=f'stem_vgain_{key_scope}')
    music_db = st.slider('Instrumental level (dB)', -24.0, 6.0, -6.0, 0.5, key=f'stem_igain_{key_scope}')
    limit = min(MAX_STEM_BYTES, max_upload_mb * 1024 * 1024)
    ready = bool(ffmpeg_ready and vocal and music)
    if any(u is not None and not 0 < u.size <= limit for u in (vocal, music)):
        st.warning(f'Each stem must be nonempty and at most {limit // (1024 * 1024)} MB.')
        ready = False
    # Streamlit file IDs identify immutable uploaded content; no full-buffer hash per slider rerun.
    identity = (scope, tuple((u.file_id, u.size) if u is not None else None for u in (vocal, music)),
                vocal_db, music_db)
    saved = st.session_state.get('_stem_mix_result') or {}
    if saved.get('identity') != identity:
        DOWNLOADS.discard(owner)
        st.session_state.pop('_stem_mix_result', None)
        saved = {}
    if st.button('Create WAV mix', disabled=not ready, key='stem_render'):
        DOWNLOADS.discard(owner)
        with st.spinner('Mixing and measuring WAV…'):
            result = render_uploaded_stems(vocal, music, vocal_db=vocal_db, instrumental_db=music_db,
                                           ffmpeg_path=ffmpeg_path, max_upload_bytes=limit)
        token = ''
        if result.get('ok'):
            audio = result.pop('audio')
            try:
                token = DOWNLOADS.put(owner, audio)
            except ValueError as exc:
                result = {'ok': False, 'error': str(exc)}
            del audio
        saved = {'identity': identity, 'result': result, 'token': token}
        st.session_state['_stem_mix_result'] = saved
    if saved:
        if st.button('Clear temporary mix', key='stem_clear'):
            DOWNLOADS.discard(owner)
            st.session_state.pop('_stem_mix_result', None)
            st.rerun()
        _download_result(owner, saved)
