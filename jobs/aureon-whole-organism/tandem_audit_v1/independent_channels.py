"""Separate scalar Kalman implementation; verified against dense covariance."""
import math
import numpy as np

def white(x,model,scale):
    if model==0:return x.copy()
    if model==1:
        rho=.9**(1/scale)
        return np.concatenate([x[:,:1],(x[:,1:]-rho*x[:,:-1])/math.sqrt(1-rho*rho)],axis=1)
    # Independent scalar Kalman covariance update and vector channel innovations.
    a,b=.97**(1/scale),.45**(1/scale)
    h,j=.65/math.sqrt(.65**2+.35**2),.35/math.sqrt(.65**2+.35**2)
    p,q,r=1.,0.,1.;m=np.zeros(x.shape[0]);n=m.copy();out=np.empty_like(x)
    for i in range(x.shape[1]):
        v=h*h*p+2*h*j*q+j*j*r;k=(p*h+q*j)/v;l=(q*h+r*j)/v
        err=x[:,i]-h*m-j*n;out[:,i]=err/math.sqrt(v)
        m=a*(m+k*err);n=b*(n+l*err)
        p,q,r=a*a*(p-k*(h*p+j*q))+1-a*a,a*b*(q-k*(h*q+j*r)),b*b*(r-l*(h*q+j*r))+1-b*b
    return out
