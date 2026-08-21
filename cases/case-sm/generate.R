# CASE-SM "Ozanib" — R implementation of the generating model.
#
# The shipped CSV is produced by generate.py, which is canonical. R and Python
# do not share a random number stream, so this script reproduces the *model*
# and the *design*, not the exact rows. Use it to see the same structural and
# statistical model expressed in R, or to make your own variant dataset.
#
# Requires: deSolve, MASS, dplyr

library(deSolve)
library(MASS)
library(dplyr)

set.seed(20260821)

truth <- list(
  TVCL = 12.0, TVVC = 60.0, TVQ = 8.0, TVVP = 90.0, TVKA = 1.2,
  WT_REF = 70, ALLO_CL = 0.75, ALLO_V = 1.00, DDI_CL_RATIO = 0.45,
  OM_CL = 0.30, OM_VC = 0.25, OM_KA = 0.45, CORR_CL_VC = 0.5,
  PROP_ERR = 0.20, ADD_ERR = 0.5, LLOQ = 1.0, MW = 465.0
)

N_SUBJECTS <- 60
DOSES_MG   <- c(25, 50, 100)
RICH_TIMES <- c(0, 0.5, 1, 2, 3, 4, 6, 8, 12, 24)
RICH_DAYS  <- c(1, 14)
TROUGH_DAYS <- c(7, 10, 21)
N_DOSES <- 21
TAU <- 24

# ---- structural model -------------------------------------------------------
# Amounts in ug so that ug / L reads directly as ng/mL.
two_cmt_oral <- function(times, dose_mg, ka, cl, vc, q, vp) {
  rhs <- function(t, y, p) {
    with(as.list(y), {
      dA_gut <- -ka * A_gut
      dA_c   <-  ka * A_gut - (cl / vc) * A_c - (q / vc) * A_c + (q / vp) * A_p
      dA_p   <-  (q / vc) * A_c - (q / vp) * A_p
      list(c(dA_gut, dA_c, dA_p))
    })
  }
  dose_times <- (seq_len(N_DOSES) - 1) * TAU
  events <- data.frame(var = "A_gut", time = dose_times,
                       value = dose_mg * 1000, method = "add")
  y0 <- c(A_gut = 0, A_c = 0, A_p = 0)
  out_times <- sort(unique(c(0, times, dose_times)))
  sol <- ode(y0, out_times, rhs, parms = NULL, events = list(data = events),
             method = "lsoda", rtol = 1e-9, atol = 1e-12)
  conc <- as.numeric(sol[, "A_c"]) / vc
  approx(sol[, "time"], conc, xout = times, ties = "ordered")$y
}

# ---- covariates -------------------------------------------------------------
n   <- N_SUBJECTS
wt  <- round(exp(rnorm(n, log(75), 0.18)), 1)
sex <- rbinom(n, 1, 0.46)
wt  <- round(ifelse(sex == 1, wt * 0.88, wt), 1)
age <- round(pmin(pmax(rnorm(n, 52, 13), 19), 84))
crcl <- round(pmin(pmax(rnorm(n, 98, 24), 32), 175))
alt <- round(pmin(pmax(exp(rnorm(n, log(24), 0.4)), 6), 180))
ddi <- rbinom(n, 1, 0.25)
dose <- sample(rep(DOSES_MG, each = n / length(DOSES_MG)))

# ---- individual parameters --------------------------------------------------
r <- truth$CORR_CL_VC
Sigma <- matrix(c(truth$OM_CL^2, r * truth$OM_CL * truth$OM_VC,
                  r * truth$OM_CL * truth$OM_VC, truth$OM_VC^2), 2, 2)
eta <- mvrnorm(n, mu = c(0, 0), Sigma = Sigma)
eta_ka <- rnorm(n, 0, truth$OM_KA)

wt_cl <- (wt / truth$WT_REF)^truth$ALLO_CL
wt_v  <- (wt / truth$WT_REF)^truth$ALLO_V
ddi_eff <- ifelse(ddi == 1, truth$DDI_CL_RATIO, 1)

cl <- truth$TVCL * wt_cl * ddi_eff * exp(eta[, 1])
vc <- truth$TVVC * wt_v  * exp(eta[, 2])
q  <- truth$TVQ  * wt_cl
vp <- truth$TVVP * wt_v
ka <- truth$TVKA * exp(eta_ka)

# ---- simulate ---------------------------------------------------------------
obs_times <- sort(unique(c(
  as.vector(outer((RICH_DAYS - 1) * TAU, RICH_TIMES, "+")),
  (TROUGH_DAYS - 1) * TAU
)))

records <- lapply(seq_len(n), function(i) {
  ipred <- two_cmt_oral(obs_times, dose[i], ka[i], cl[i], vc[i], q[i], vp[i])
  dv <- pmax(ipred * (1 + rnorm(length(ipred), 0, truth$PROP_ERR)) +
               rnorm(length(ipred), 0, truth$ADD_ERR), 0)
  obs <- data.frame(ID = i, TIME = obs_times, AMT = NA_real_, DV = dv,
                    EVID = 0, IPRED_TRUE = ipred)
  dos <- data.frame(ID = i, TIME = (seq_len(N_DOSES) - 1) * TAU,
                    AMT = dose[i], DV = NA_real_, EVID = 1,
                    IPRED_TRUE = NA_real_)
  rbind(obs, dos) |>
    mutate(DOSE = dose[i], WT = wt[i], AGE = age[i], SEX = sex[i],
           CRCL = crcl[i], ALT = alt[i], DDI = ddi[i])
})

df <- bind_rows(records) |>
  mutate(NTIME = TIME %% TAU,
         DAY = floor(TIME / TAU) + 1,
         MDV = as.integer(is.na(DV)),
         CMT = ifelse(EVID == 1, 1, 2),
         BLQ = as.integer(EVID == 0 & !is.na(DV) & DV < truth$LLOQ),
         DV  = ifelse(BLQ == 1, NA_real_, DV),
         MDV = ifelse(BLQ == 1, 1L, MDV)) |>
  arrange(ID, TIME, desc(EVID))

message(sprintf("rows: %d   subjects: %d   BLQ: %d",
                nrow(df), n, sum(df$BLQ)))
# write.csv(df, "cases/case-sm/data/ozanib_pk_R.csv", row.names = FALSE)
