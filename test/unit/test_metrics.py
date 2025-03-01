import os
import pytest
import numpy as np
import porespy as ps
from skimage import io
from edt import edt
from pathlib import Path
import scipy.ndimage as spim
from skimage.morphology import ball
from numpy.testing import assert_allclose
ps.settings.tqdm['disable'] = True


class MetricsTest():

    def setup_class(self):
        np.random.seed(0)
        self.im2D = ps.generators.lattice_spheres(shape=[101, 101],
                                                  r=5, spacing=15,
                                                  lattice='square')
        self.im2D_big = ps.generators.lattice_spheres(shape=[500, 500],
                                                      r=10, spacing=25,
                                                      lattice='square')
        self.im3D = ps.generators.lattice_spheres(shape=[51, 51, 51],
                                                  r=4, spacing=14,
                                                  lattice='cubic')
        self.blobs = ps.generators.blobs(shape=[101, 101, 101], porosity=0.5,
                                         blobiness=[1, 2, 3])
        path = Path(os.path.realpath(__file__),
                    '../../../test/fixtures/partitioned_regions.tif')
        self.regions = np.array(io.imread(path))

    def test_porosity(self):
        phi = ps.metrics.porosity(im=self.im2D)
        assert np.allclose(phi, 0.66856)

    def test_tpcf_fft_2d(self):
        tpcf_fft_1 = ps.metrics.two_point_correlation(self.im2D)
        tpcf_fft_2 = ps.metrics.two_point_correlation(self.im2D_big)
        # autocorrelation fn should level off at around the porosity
        t = 0.2
        phi1 = ps.metrics.porosity(im=self.im2D)
        assert np.sqrt((np.mean(tpcf_fft_1.probability[-5:]) - phi1)**2) < t
        phi2 = ps.metrics.porosity(im=self.im2D_big)
        assert np.sqrt((np.mean(tpcf_fft_2.probability[-5:]) - phi2)**2) < t
        # Must raise error if 1D image is supplied
        with pytest.raises(Exception):
            _ = ps._metrics.two_point_correlation(np.random.rand(10))

    def test_tpcf_fft_3d(self):
        tpcf_fft = ps.metrics.two_point_correlation(self.im3D)
        t = 0.2
        phi1 = ps.metrics.porosity(im=self.im3D)
        assert np.sqrt((np.mean(tpcf_fft.probability[-5:]) - phi1)**2) < t

    def test_pore_size_distribution(self):
        mip = ps.filters.porosimetry(self.im3D)
        psd = ps.metrics.pore_size_distribution(mip)
        assert np.sum(psd.satn) == 1.0

    def test_two_point_correlation_bf(self):
        from porespy.metrics._funcs import two_point_correlation_bf
        tpcf_bf = two_point_correlation_bf(self.im2D, spacing=4)
        # autocorrelation fn should level off at around the porosity
        tol = 0.05
        phi1 = ps.metrics.porosity(im=self.im2D)
        assert np.sqrt((np.mean(tpcf_bf.probability[-5:]) - phi1)**2) < tol

    def test_rev(self):
        rev = ps.metrics.representative_elementary_volume(self.blobs)
        assert (np.mean(rev.porosity) - 0.5)**2 < 0.05

    def test_radial_density(self):
        dt = edt(self.blobs)
        den = ps.metrics.radial_density_distribution(dt)
        assert den.cdf.max() == 1

    def test_props_to_DataFrame(self):
        label = spim.label(self.im2D)[0]
        rp = ps.metrics.regionprops_3D(label)
        ps.metrics.props_to_DataFrame(rp)

    def test_prop_to_image(self):
        label = spim.label(self.im2D)[0]
        rp = ps.metrics.regionprops_3D(label)
        ps.metrics.prop_to_image(rp, self.im2D.shape, 'solidity')

    def test_porosity_profile(self):
        im = ps.generators.lattice_spheres(shape=[999, 999],
                                           r=15, spacing=38)
        p = ps.metrics.porosity_profile(im, axis=0)
        assert p.max() == 1.0
        assert_allclose(p.min(), 0.24524524524524523)

    def test_porosity_profile_ndim_check(self):
        ps.metrics.porosity_profile(self.im2D, axis=0)
        ps.metrics.porosity_profile(self.im2D, axis=1)
        with pytest.raises(Exception):
            ps.metrics.porosity_profile(self.im2D, axis=2)

    def test_linear_density(self):
        im = ps.filters.distance_transform_lin(self.im2D, axis=0, mode='both')
        ps.metrics.lineal_path_distribution(im)

    def test_chord_length_distribution_2D(self):
        chords = ps.filters.apply_chords(self.im2D)
        cld = ps.metrics.chord_length_distribution(chords,
                                                   normalization='length')
        assert not hasattr(cld, "LogL")
        cld = ps.metrics.chord_length_distribution(chords,
                                                   normalization='length',
                                                   log=1)
        assert hasattr(cld, "LogL")
        with pytest.raises(Exception):
            cld = ps.metrics.chord_length_distribution(chords,
                                                       normalization='unsupported_norm')

    def test_chord_length_distribution_3D(self):
        chords = ps.filters.apply_chords(self.im3D)
        ps.metrics.chord_length_distribution(chords, normalization='length')

    def test_chord_counts(self):
        im = np.ones([100, 50])
        crds = ps.filters.apply_chords(im, spacing=1, trim_edges=False)
        c = ps.metrics.chord_counts(crds)
        assert np.all(c == 100)
        crds = ps.filters.apply_chords(im, spacing=1, trim_edges=False, axis=1)
        c = ps.metrics.chord_counts(crds)
        assert np.all(c == 50)

    @pytest.mark.skip(reason="Passes locally, fails on GitHub!")
    def test_mesh_surface_area(self):
        region = self.regions == self.regions.max()
        mesh = ps.tools.mesh_region(region)
        a = ps.metrics.mesh_surface_area(mesh)
        # assert np.around(a, decimals=2) == 258.3
        b = ps.metrics.mesh_surface_area(verts=mesh.verts, faces=mesh.faces)
        # assert np.around(b, decimals=2) == np.around(a, decimals=2)
        with pytest.raises(Exception):
            mesh = ps.metrics.mesh_surface_area(mesh=None)

    def test_region_surface_areas(self):
        regions = self.regions
        areas = ps.metrics.region_surface_areas(regions)
        assert not np.any(np.isnan(areas))

    @pytest.mark.skip(reason="Passes locally, fails on GitHub!")
    def test_region_interface_areas(self):
        regions = self.regions
        areas = ps.metrics.region_surface_areas(regions)
        ia = ps.metrics.region_interface_areas(regions, areas)
        # assert np.all(ia.conns[0] == [2, 19])
        # assert np.around(ia.area[0], decimals=2) == 3.59

    def test_region_volumes(self):
        regions = self.regions[:50, :50, :50]
        vols_march = ps.metrics.region_volumes(regions=regions)
        vols_vox = ps.metrics.region_volumes(regions=regions, mode='voxel')
        assert_allclose(vols_march[:5], [1498.85320453, 2597.90798652,
                                         2158.34548652, 1281.17978573, 1172.39853573])
        assert_allclose(vols_vox[:5], [1540., 2648., 2206., 1320., 1210.])
        assert_allclose(np.mean(vols_march), 1907.8062788852674)
        assert_allclose(np.mean(vols_vox), 1952.125)

    def test_region_volumes_for_sphere(self):
        region = ball(10)
        vol_march = ps.metrics.region_volumes(regions=region)
        vol_vox = ps.metrics.region_volumes(region, mode='voxel')
        assert_allclose(vol_march, 4102.28678846)
        assert_allclose(vol_vox, 4169.)

    def test_phase_fraction(self):
        im = np.reshape(np.random.randint(0, 10, 1000), [10, 10, 10])
        labels = np.unique(im, return_counts=True)[1]
        counts = ps.metrics.phase_fraction(im, normed=False)
        counts = np.fromiter(counts.values(), int)
        assert np.all(labels == counts)
        fractions = ps.metrics.phase_fraction(im, normed=True)
        fractions = np.fromiter(fractions.values(), float)
        assert np.isclose(fractions.sum(), 1)
        assert np.allclose(fractions, counts / counts.sum())
        # The method must also work on boolean images
        counts = ps.metrics.phase_fraction(im.astype(bool))
        assert counts[0] == (im == 0).sum() / im.size
        assert counts[1] == (im != 0).sum() / im.size
        # The method should also work on float images
        im = np.array([0.5, 0.5, 1.5, 1.5, 12, 1.5, 12, 12, 12, 12])
        fractions = ps.metrics.phase_fraction(im, normed=True)
        k = np.fromiter(fractions.keys(), float)
        v = np.fromiter(fractions.values(), float)
        assert np.allclose(k, [0.5, 1.5, 12])
        assert np.allclose(v, [0.2, 0.3, 0.5])

    def test_representative_elementary_volume(self):
        im = ps.generators.lattice_spheres(shape=[999, 999],
                                           r=15, offset=4)
        rev = ps.metrics.representative_elementary_volume(im)
        assert_allclose(np.average(rev.porosity), im.sum() / im.size, rtol=1e-1)

        im = ps.generators.lattice_spheres(shape=[151, 151, 151],
                                           r=9, offset=4)
        rev = ps.metrics.representative_elementary_volume(im)
        assert_allclose(np.average(rev.porosity), im.sum() / im.size, rtol=1e-1)

    # def test_geometric_tortuosity_2d(self):
        # np.random.seed(0)
        # im = ps.generators.blobs(shape=[300, 300], porosity=0.6, blobiness=2)
        # out = ps.metrics.geometrical_tortuosity(im)
        # assert np.size(out) == 1
        # assert out >= 1

    # def test_geometric_tortuosity_3d(self):
        # np.random.seed(0)
        # im = ps.generators.blobs(shape=[100, 100, 100], porosity=0.6, blobiness=2)
        # out = ps.metrics.geometrical_tortuosity(im)
        # assert np.size(out) == 1
        # assert out >= 1

    # def test_geometric_tortuosity_points_2d(self):
        # This function is not quite ready yet
        # np.random.seed(0)
        # im = ps.generators.blobs(shape=[300, 300], porosity=0.6, blobiness=2)
        # out = ps.metrics.geometrical_tortuosity_points(im)
        # assert np.shape(out[0])[0] ==np.shape(out[0])[1]
        # assert np.size(out[1]) == 1
        # assert out[1] >= 1

    # def test_geometric_tortuosity_points_3d(self):
        # This function is not quite ready yet
        # np.random.seed(0)
        # im = ps.generators.blobs(shape=[50, 50, 50], porosity=0.6, blobiness=2)
        # out = ps.metrics.geometrical_tortuosity_points(im)
        # assert np.shape(out[0])[0] ==np.shape(out[0])[1]
        # assert np.size(out[1]) == 1
        # assert out[1] >= 1

    def test_pc_curve(self):
        im = ps.generators.blobs(shape=[100, 100], porosity=0.7)
        sizes = ps.filters.porosimetry(im=im)
        pc = ps.metrics.pc_curve(sizes=sizes, im=im)
        assert hasattr(pc, 'pc')
        assert hasattr(pc, 'snwp')

    def test_pc_curve_from_ibip(self):
        im = ps.generators.blobs(shape=[100, 100], porosity=0.7)
        seq, sizes = ps.filters.ibip(im=im)
        pc = ps.metrics.pc_curve(im=im, sizes=sizes, seq=seq)
        assert hasattr(pc, 'pc')
        assert hasattr(pc, 'snwp')


if __name__ == '__main__':
    t = MetricsTest()
    self = t
    t.setup_class()
    for item in t.__dir__():
        if item.startswith('test'):
            print(f"Running test: {item}")
            t.__getattribute__(item)()
