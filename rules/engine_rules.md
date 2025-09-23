# Engine Rules

## Sampling
- FPS_target = 2~5
- N_consecutive = 5s × FPS_target (승급)
- M_consecutive = 2s × FPS_target (하향)

## Pre-filters
- ROI 밖 박스 제거
- HSV 불색 비율 p (H≈0–60°, S>0.5, V>0.5)
  - p < 0.08 → 제거
- Person 억제: person과 IoU>0.5 & p<0.20 → 제거

## Scores
- fire_raw(t) = max(conf of fire) or 0
- smoke_raw(t) = max(conf of smoke) or 0
- EMA: F(t)=α·fire_raw+(1-α)·F(t-1), S(t)=α·smoke_raw+(1-α)·S(t-1), α=0.4
- growth(t)=ReLU(ΔS)+ReLU(ΔF)
- hazard(t)=max(0.6·S, 0.8·F)+0.4·growth
- SSE 주기: 0.2s

## States (히스테리시스 포함)
- PRE_FIRE: S>0.30 or F>0.25 (N연속)
- SMOKE_DETECTED: S>0.50 (N연속)
- FIRE_GROWING: F>0.60 or hazard>0.70 (N연속)
- CALL_119: hazard>0.85 (N연속)
- 하향: 각 임계치의 0.8배 이하 M연속