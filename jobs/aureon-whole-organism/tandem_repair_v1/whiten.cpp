#include <cmath>
#include <cstdint>

// Row-major series. Coefficients describe exact scalar Kalman innovations for
// a stationary sum of independent AR(1) processes; no periodic padding.
extern "C" void whiten(const double* input, double* output,
                       const int64_t* models, int64_t batch, int64_t channels,
                       int64_t length, double rho_ar, double rho_slow,
                       double rho_fast, const double* k0, const double* k1,
                       const double* inverse_sd) {
    const double norm = std::sqrt(.65*.65 + .35*.35);
    const double h0=.65/norm, h1=.35/norm;
    const double ar_scale=std::sqrt(1.-rho_ar*rho_ar);
    for (int64_t b=0;b<batch;++b) {
        for (int64_t c=0;c<channels;++c) {
            const double* x=input+(b*channels+c)*length;
            double* y=output+(b*channels+c)*length;
            if(models[b]==0) {
                for(int64_t t=0;t<length;++t)y[t]=x[t];
            } else if(models[b]==1) {
                y[0]=x[0];
                for(int64_t t=1;t<length;++t)y[t]=(x[t]-rho_ar*x[t-1])/ar_scale;
            } else {
                double m0=0.,m1=0.;
                for(int64_t t=0;t<length;++t) {
                    const double error=x[t]-h0*m0-h1*m1;
                    y[t]=error*inverse_sd[t];
                    m0=rho_slow*(m0+k0[t]*error);
                    m1=rho_fast*(m1+k1[t]*error);
                }
            }
        }
    }
}
