from astropy.table import table
from core.data import *
from astropy import log
import numpy as np
import astropy.constants as const
import core.parameter as par
import core.data as dt
import astropy.wcs as wcs

class Universe:
    """
    A synthetic universe where to put synthetic objects.
    """

    def __init__(self):
        self.sources = dict()

    def create_source(self, name, pos):
        """
        A source needs a name and a spatial position (alpha,delta).
        """
        self.sources[name] = Source(name, pos)

    def add_component(self, source_name, model):
        """
        To add a component a Component object must be instantiated (model), and added to 
        a source called source_name.
        """
        self.sources[source_name].add_component(model)

    def _gen_sources_table(self):
        """
        Will generate a table with the following columns:
            - Component ID
            - Source name
            - Model
            - Alpha
            - Delta
            - Red shift (z)
            - Radial velocity

        :return: an astropy table.
        """

        # create columns for all fields.
        col_comp_id = []
        col_source_name = []
        col_model = []
        col_alpha = []
        col_delta = []
        col_redshift = []
        col_radial_velocity = []

        # run through all sources and components, and add those values to the above lists.
        for source in self.sources:
            for component in self.sources[source].comp:
                col_comp_id.append(component.comp_name)
                col_source_name.append(self.sources[source].name)
                col_model.append("Not yet.")
                col_alpha.append(component.pos[0].value)
                col_delta.append(component.pos[1].value)
                col_redshift.append(component.get_redshift().value)
                col_radial_velocity.append(component.get_velocity().value)

        # create two lists for the table, this is to not pollute the table construction line.
        col_values = [col_comp_id, col_source_name, col_model, col_alpha, col_delta, col_redshift, col_radial_velocity]
        col_names = ["Comp ID", "Source name", "Model", "Alpha", "Delta", "Redshift", "Radial Vel"]
        return table.Table(col_values, names=col_names)
    
    def gen_cube(self, pos, ang_res, fov, freq, spe_res, bw, noise):
        """
        Returns a Cube object where all the sources within the FOV and BW are projected, and
        a dictionary with a sources astropy Table and all the parameters of the components
        in the succesive Tables

        This function needs the following parameters:
        - name    : name of the cube
        - pos     : right-ascension and declination center
        - ang_res : angular resolution x2
        - fov     : angular field of view x 2
        - freq    : spectral center (frequency)
        - spe_res : spectral resolution
        - bw  : spectral bandwidth
        """
            # Create a new WCS object.
        pos=par.to_deg(pos)
        ang_res=par.to_deg(ang_res)
        fov=par.to_deg(fov)
        #print pos,ang_res,fov
        freq=par.to_hz(freq)
        spe_res=par.to_hz(spe_res)
        bw=par.to_hz(bw)
        #print freq,spe_res,bw
        w = wcs.WCS(naxis=3)
        w.wcs.crval = np.array([pos[0].value, pos[1].value,freq.value])
        w.wcs.cdelt = np.array([ang_res[0].value, ang_res[1].value,spe_res.value])
        mm = np.array([int(abs(fov[0]/ang_res[0])),int(abs(fov[1]/ang_res[1])),int(abs(bw/spe_res))])
        w.wcs.crpix = mm/2.0
        w.wcs.ctype = ["RA---SIN", "DEC--SIN","FREQ"]
        data=np.zeros((mm[2],mm[1],mm[0]))
        #w.wcs.print_contents()
        cube = dt.AcaData(data,w,None,u.Jy/u.beam)

        tables = dict()
        tables['sources'] = self._gen_sources_table()

        for source in self.sources:
            log.info('Projecting source ' + source)
            dsource = self.sources[source].project(cube,noise/50.0)
            tables.update(dsource)
        cube.add_flux(2*noise*(np.random.random(cube.data.shape) - 0.5))
        return cube, tables

    def save_cube(self, cube, filename):
        """
        Wrapper function that saves a cube into a FITS (filename).
        """
        cube.save_fits(self.sources, filename)

class Source:
    """
    A generic source of electromagnetic waves with several components.
    """

    def __init__(self, name, pos):
        """
        :param name:    a name of the source
        """

        self.pos=par.to_deg(pos)
        self.name = name
        self.comp = list()

        log.info('Source \'' + name + '\' added\n')

    def add_component(self, model):
        """
        Defines a new component from a model.
        """

        code = self.name + '::' + str(len(self.comp) + 1)

        # create a deep copy of the model.
        model_cpy = copy.deepcopy(model)
        model_cpy.register(code, self.pos)
        self.comp.append(model_cpy)

        log.info('Added component ' + code + ' with model ' + model_cpy.info())

    def project(self, cube,limit):
        """
        Projects all components in the source to a cube.
        """

        component_tables = dict()
        log.info('Projecting Source at '+str(self.pos))
        for component in self.comp:
            log.info('Projecting ' + component.comp_name)
            table = component.project(cube,limit)

            if table is not None:
                component_tables[component.comp_name] = table

        return component_tables

class Component:
    """Abstract component model"""

    def __init__(self):
        """
        Assume object in rest velocity/redshift
        """

        self.z = 0 * u.Unit("")

    def set_velocity(self, rvel):
        """Set radial velocity rvel. If rvel has no units, we assume km/s"""
        c = const.c.to('m/s')
        rvel = par.to_m_s(rvel)

        self.z = np.sqrt((1 + rvel/c) / (1 - rvel/c)) - 1

    def set_redshift(self, z):
        """Set the redshift"""
        self.z = z
 
    def get_velocity(self):
        """
        Get radial velocity rvel
        """
        z = self.z
        c = const.c.to('m/s')

        rv = c * (2 * z + np.square(z)) / (2 * z + np.square(z) + 2)

        return rv

    def get_redshift(self):
        """
        Get the redshift
        """

        return self.z

    def info(self):
        """
        Print relevant information of the component
        """

        return "(none)"

    def register(self, comp_name, pos):
        """
        Register the component name and angular position (alpha, delta)
        """

        self.comp_name = comp_name
        self.pos = pos

    def project(self, cube, limit):
        """
        Project the component in the cube and return the component astropy Table
        """
        pass
