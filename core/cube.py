import numpy as np
import copy

from astropy import constants as const
from astropy import units as u
from astropy.io import fits 
from astropy import log
import astropy.nddata as ndd
import astropy.wcs as astrowcs

# ## Helper constants ###
#SPEED_OF_LIGHT = 299792458.0
#S_FACTOR = 2.354820045031  # sqrt(8*ln2)
#DEG2ARCSEC = 3600.0

#def fwhm2sigma(freq,fwhm):
#    """
#    Compute the sigma in Hz given a frequency in Hz and a fwhm in m/s
#    """
#    sigma = (fwhm / S_FACTOR) * (freq / const.c.value)
#    return sigma

#def doppler(freq,rv):
#    freq_new = math.sqrt((1 + rv / const.c.value) / (1 - rv / const.c.value)) * freq
#    return freq_new

#def cube_data_unravel(data,idx):
#   return data.reshape((idx[5]-idx[4],idx[3]-idx[2],idx[1]-idx[0]))

#def cube_data_stack(data):
#   return data.sum(axis=0)

class Cube(ndd.NDData):
    """
    A generic represenation of astronomical data.
    A spectra is a 3D cube with ra_axis and dec_axis of size 1
    An image is a 3D cube with nu_axis of size 1
    A spectroscopic cube is a 3D cube
    Stokes 4D cubes are not supported.
    """
    def __init__(self,data,meta):
        """ data = numpy data
            meta = header of fits
        """
        mask=np.isnan(data)
        bscale=meta['BSCALE']
        bzero=meta['BZERO']
        bsu=meta['BUNIT']
        # Hack to correct wrong uppercased units generated by CASA
        bsu=bsu.lower()
        bsu=bsu.replace("jy","Jy")
        
        # Create astropy units
        bunit=u.Unit(bsu,format="fits")
        
        if len(data.shape) != 4:
            log.error("Only 4D data is allowed for now (like CASA-generated ones). Talk to the core team to include your datatype")
            raise TypeError
        
        # Put data in physically-meaninful values
        data=data*bscale+bzero
        wcs=astrowcs.WCS(meta)

        # Call super constructor with transposed data 
        ndd.NDData.__init__(self,data,None,mask,wcs,meta,bunit)

    def copy(self):
        return copy.deepcopy(self)

    def emptyLike(self):
        dat=np.zeros_like(self.data)
        cb=Cube(dat,self.meta)
        return cb
     
    def _slice(self,lower,upper):
        if lower=None:
            lower=(0,0,0,0)
        if upper=None:
            upper=self.data.shape
        if isinstance(lower,tuple):
            lower=np.array(lower)
        if isinstance(upper,tuple):
            upper=np.array(upper)
        llc=lower < 0
        ulc=lower > self.data.shape
        luc=upper < 0
        uuc=upper > self.data.shape
        if llc.any():
            log.warning("Negative lower index "+str(lower)+". Correcting to zero.")
            lower[llc]=0
        if ulc.any():
            log.warning("Lower index out of bounds "+str(lower)+" > "+str(self.data.shape)+". Correcting to max.")
            upper[ulc]=self.data.shape[ulc]
        if luc.any():
            log.warning("Negative upper index "+str(upper)+". Correcting to zero.")
            lower[luc]=0
        if uuc.any():
            log.warning("Upper index out of bounds "+str(upper)+" > "+str(self.data.shape)+". Correcting to max.")
            upper[uuc]=self.data.shape[uuc]
        return [slice(lower[0],upper[0]),slice(lower[1],upper[1]),slice(lower[2],upper[2]),slice(lower[3],lower[3])]
          
    def getStackedData(self,lower=None,upper=None,axes=(0,1)):
        sli=self._slice(lower,upper)
        return self.data[sli].sum(axes)

    def addFlux(self,flux,lower=None,upper=None)
        sli=self._slice(lower,upper)
        fl=np.array([0,0,0,0])
        fu=np.array(flux.shape)
        for i in range(0,4):
           if sli[i].start == 0:
              fl[i]=flux.shape[i] - sli[i].stop
           if sli[i].stop == self.data.shape[i]
              fu[i]=sli[i].stop - sli[i].start
        self.data[sli]+=flux[fl[0]:fu[0],fl[1]:fu[1],fl[2]:fu[2],fl[3]:fu[3]]

    def max(self):
        index=np.unravel_index(self.data.argmax(),self.data.shape)
        y=self.data[index]
        return (y,index)

    def min(self):
        index=np.unravel_index(self.data.argmin(),self.data.shape)
        y=self.data[index]
        return (y,index)
#HERE

    def compute_window(self,center,window):
        ra_ui=np.argmin(np.abs(self.ra_axis-center[0]-window[0]))+1;
        ra_li=np.argmin(np.abs(self.ra_axis-center[0]+window[0]));
        dec_ui=np.argmin(np.abs(self.dec_axis-center[1]-window[1]))+1;
        dec_li=np.argmin(np.abs(self.dec_axis-center[1]+window[1]));
        nu_ui=np.argmin(np.abs(self.nu_axis-center[2]-window[2]))+1;
        nu_li=np.argmin(np.abs(self.nu_axis-center[2]+window[2]));
        return (ra_li,ra_ui,dec_li,dec_ui,nu_li,nu_ui)
        

    def feature_space(self,center,window):
        ra_ci=np.argmin(np.abs(self.ra_axis-center[0]));
        ra_ui=np.argmin(np.abs(self.ra_axis-center[0]-window[0]))+1;
        ra_li=np.argmin(np.abs(self.ra_axis-center[0]+window[0]));
        dec_ci=np.argmin(np.abs(self.dec_axis-center[1]));
        dec_ui=np.argmin(np.abs(self.dec_axis-center[1]-window[1]))+1;
        dec_li=np.argmin(np.abs(self.dec_axis-center[1]+window[1]));
        nu_ci=np.argmin(np.abs(self.nu_axis-center[2]));
        nu_ui=np.argmin(np.abs(self.nu_axis-center[2]-window[2]))+1;
        nu_li=np.argmin(np.abs(self.nu_axis-center[2]+window[2]));
        

        crval1=self.ra_axis[ra_ci]
        crval2=self.dec_axis[dec_ci]
        crval3=self.nu_axis[nu_ci]
        crpix1=ra_ci - ra_li 
        crpix2=dec_ci - dec_li 
        crpix3=nu_ci - nu_li 
        naxis1=ra_ui-ra_li  
        naxis2=dec_ui-dec_li 
        naxis3=nu_ui-nu_li 
        ra_axis=np.linspace(crval1-crpix1*self.ra_delta,crval1+(naxis1-crpix1)*self.ra_delta, num=naxis1)
        dec_axis=np.linspace(crval2-crpix2*self.dec_delta,crval2+(naxis2-crpix2)*self.dec_delta, num=naxis2)
        nu_axis=np.linspace (crval3-crpix3*self.nu_delta,crval3+(naxis3-crpix3)*self.nu_delta, num=naxis3)
        adn=np.meshgrid(nu_axis,dec_axis,ra_axis, indexing='ij')
        X=np.empty((3,len(ra_axis)*len(dec_axis)*len(nu_axis)))
        X[2]=adn[0].ravel()
        X[1]=adn[1].ravel()
        X[0]=adn[2].ravel()
        yidx=(ra_li,ra_ui,dec_li,dec_ui,nu_li,nu_ui)
        return X,yidx

    def _add_HDU(self, hdu):
        self.hdulist.append(hdu)

    def save_fits(self, filename):
        """ Simple as that... saves the whole cube """
        self.hdulist.writeto(filename, clobber=True)

    def _updatefig(self, j):
        """ Animate helper function """
        self.im.set_array(self.data[j, :, :])
        return self.im,

    def estimate_ssnr(self):
        mneg=np.abs((self.data[self.data < 0]).mean())
        mpos=(self.data[self.data > mneg]).mean()
        s=abs(mpos-mneg)
        ssnr=s/(s+mneg)
        return ssnr

    def animate(self, inte, rep=True):
        """ Simple animation of the cube.
            - inte       : time interval between frames
            - rep[=True] : boolean to repeat the animation
          """
        fig = plt.figure()
        self.im = plt.imshow(self.data[0, :, :], cmap=plt.get_cmap('jet'), vmin=self.data.min(), vmax=self.data.max(), \
                             extent=(
                                 self.alpha_border[0], self.alpha_border[1], self.delta_border[0],
                                 self.delta_border[1]))
        ani = animation.FuncAnimation(fig, self._updatefig, frames=range(len(self.freq_axis)), interval=inte, blit=True,
                                      repeat=rep)
        plt.show()

#    def index_center(self,index):
#        ra=(self.ra_axis[index[0]]+self.ra_axis[index[1]-1])/2.0
#        dec=(self.dec_axis[index[2]]+self.dec_axis[index[3]-1])/2.0
#        nu=(self.nu_axis[index[4]]+self.nu_axis[index[5]-1])/2.0
#        return np.array([ra,dec,nu])

   #def ravel(self,idx=np.array([])):
   #     if len(idx)!=6:
   #        lss=self.data
   #     else:
   #        lss=self.data[idx[4]:idx[5],idx[2]:idx[3],idx[0]:idx[1]]
   #     return lss.ravel()
#    def standarize(self):
#        y_min=self.data.min()
#        self.data=self.data - y_min
#        y_fact=self.data.sum()
#        self.data=self.data/y_fact
#        ra_min=self.ra_axis[0]
#        self.ra_axis=self.ra_axis - ra_min
#        ra_fact=self.ra_axis[-1]
#        self.ra_axis=self.ra_axis/ra_fact
#        self.ra_delta=self.ra_delta/ra_fact
#        dec_min=self.dec_axis[0]
#        self.dec_axis=self.dec_axis - dec_min
#        dec_fact=self.dec_axis[-1]
#        self.dec_axis=self.dec_axis/dec_fact
#        self.dec_delta=self.dec_delta/dec_fact
#        nu_min=self.nu_axis[0]
#        self.nu_axis=self.nu_axis - nu_min
#        nu_fact=self.nu_axis[-1]
#        self.nu_axis=self.nu_axis/nu_fact
#        self.nu_delta=self.nu_delta/nu_fact
#        return (y_min,y_fact,ra_min,ra_fact,dec_min,dec_fact,nu_min,nu_fact)

#    def unstandarize(self,(y_min,y_fact,ra_min,ra_fact,dec_min,dec_fact,nu_min,nu_fact#)):
#        self.data=self.data*y_fact + y_min
#        self.ra_axis=self.ra_axis*ra_fact + ra_min
#        self.dec_axis=self.dec_axis*dec_fact + dec_min
#        self.nu_axis=self.nu_axis*nu_fact + nu_fact
#        self.ra_delta=self.ra_delta*ra_fact
#        self.dec_delta=self.dec_delta*dec_fact
#        self.nu_delta=self.nu_delta*nu_fact

#    def max_energy(self,sc,idx):
#          target=self.data[idx[4]:idx[5],idx[2]:idx[3],idx[0]:idx[1]]
#          if target.shape != sc.shape:
#            si=np.array([0,sc.shape[2],0,sc.shape[1],0,sc.shape[0]])
#            mm=target.min()
#            datum=mm*np.ones_like(sc)
#            if idx[4] == 0:
#               si[4]=si[5]  - idx[5]
#            if idx[2] == 0:
#               si[2]=si[3]  - idx[3]
#            if idx[0] == 0:
#               si[0]=si[1]  - idx[1]
#            if idx[5] == self.nu_axis.size:
#               si[5] =idx[5] - idx[4] 
#            if idx[3] == self.dec_axis.size:
#               si[3] =idx[3] - idx[2] 
#            if idx[1] == self.ra_axis.size:
#               si[1] =idx[1] - idx[0]
#            datum[si[4]:si[5],si[2]:si[3],si[0]:si[1]]=target
#            #max_energy=(self.data[idx[4]:idx[5],idx[2]:idx[3],idx[0]:idx[1]]/sc[si[4]:si[5],si[2]:si[3],si[0]:si[1]]).min()
#          else:
#            datum=target
#          max_energy=(datum/sc).min()
#          return max_energy

