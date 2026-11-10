from pathlib import Path
import hashlib,json,math,zipfile,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent.parent;p=ROOT/'work/lidar-diagnostic-v2';cfg=json.loads((p/'diagnostic-config.json').read_text())
sources=json.loads((p/'paper-provenance.json').read_text())
for s in sources:
    native=p/(s['blob']+'.docx');raw=native.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==s['sha256']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==s['blob']
    with zipfile.ZipFile(native) as z:
        if 'docProps/core.xml' in z.namelist():
            xml=ET.fromstring(z.read('docProps/core.xml'))
            s['document_metadata']={child.tag.split('}')[-1]:child.text for child in xml if child.text}
        else:s['document_metadata']=None
    s['earliest_known_git_addition']=min(v['committed'] for v in s['versions'])
phi=(1+math.sqrt(5))/2;res=[]
for g in cfg['geometries']:
    fmin=1/max(g['rows']*g['dy_m'],g['cols']*g['dx_m'])
    fmax=min(.5/g['dy_m'],.5/g['dx_m'])
    shells=[]
    for n in range(10):
        radius=15000/phi**(2*n);wavelength=2*math.pi*radius;freq=1/wavelength
        shells.append(dict(index=n,radius_m=radius,wavelength_m=wavelength,frequency=freq,within_full_annulus_sampling_band=fmin<=freq<=fmax))
    res.append(dict(grid=g,minimum_nonzero_axis_frequency=fmin,full_annulus_nyquist=fmax,
                    conservative_minimum_full_annulus_wavelength_m=1/fmax,shells=shells,
                    resolvable_shell_centres=[r['index'] for r in shells if r['within_full_annulus_sampling_band']],
                    target_core_sigma_ns_m=[2*g['dy_m'],5.5*g['dy_m']],target_core_sigma_ew_m=[2*g['dx_m'],5.5*g['dx_m']]))
result=dict(schema='lidar-source-coverage/v1',sources=sources,resolution=res,
            coverage={'paper_amplitude_fourier_filter':'implemented; eleven original filters tested and retained',
                      'coherence_phase_to_spatial_core_boundary':'not implemented or validated by this amplitude benchmark; Fourier-plane phase versus spatial-location mapping must be specified',
                      'v2_acoustic_material_specific_filters':'not implemented by this benchmark; reported 5.30–12.15 m seed wavelengths lie below both grids sampling capability',
                      'physical_subsurface_material_ground_truth':'absent in benchmark',
                      'integrated_legacy_calendar_twig_timed_reading':'retained in overall research scope; this image-amplitude experiment cannot test that story'},
            corrections=['Nuisance indices 0,1,2 all include fractal terrain, planar slope and directional ridge; they are not isolated nuisance mechanisms.',
                         'Original masked patches replace pixels with zero before final centering, not a newly computed whole-image mean.',
                         'Original AUROC and average-precision code is order-dependent for ties; new metrics group ties.',
                         'Original aggregate file glob includes stdout JSON sidecars and its duplicate-ID guard can fail; new analysis enumerates exact expected filenames.',
                         'Original aggregate names Bonferroni multiplication Holm conservative; new analysis implements monotone Holm adjustment explicitly.',
                         'Old protocol timestamp 19:30 UTC follows submission receipt 19:13:43 UTC on 2026-08-26; do not assert verified prior registration from these documents.',
                         'Targets are sampled in pixels, so the two grid arms also change physical target dimensions. Resolution alone cannot explain cross-grid differences.'],
            phase_fact='The paper amplitude transfer is real and nonnegative. Where its transfer is positive it preserves each Fourier coefficient phase; a frequency-plane coefficient is not by itself a local spatial phase measurement.',
            chronology_limit='Git additions and editable document metadata bound located versions, not definitive first authorship dates.')
(ROOT/'outputs/lidar-source-coverage-20260912.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(dict(resolution=res),indent=2))
