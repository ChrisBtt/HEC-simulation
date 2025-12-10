#!/usr/bin/env bash

# To run:
# chmod +x beam_sweep.sh
# ./beam_sweep.sh

set -u
export LC_ALL=C

TOPAS_BIN="/root/shellScripts/topas"  # adjust Topas path here
BASE="/mnt/e/Christoph/applications/hec-dose-distribution/TOPAS_macros/broad_beam/simulation.txt" # base macro
OUTDIR="/mnt/e/Christoph/applications/hec-dose-distribution/TOPAS_simulation_data/beam_experiment"
mkdir -p "$OUTDIR"

[[ -x "$TOPAS_BIN" ]] || { echo "No topas at $TOPAS_BIN"; exit 1; }
[[ -f "$BASE" ]]      || { echo "No base macro at $BASE"; exit 1; }

# ========================= Main settings =========================
HIST=10000000        # single number of histories
T=32                # single number of threads
REPS=1              # single repetition

# beam energies and diameters
SPECTRA=("6MV" "10MV")
DIAMS=(10 5 1)      # cm

CSV="$OUTDIR/results.csv"
echo "energy,diam_cm,hist,threads,wall_s,user_s,sys_s,rss_kb,eps,log" > "$CSV"

# key=value extractor for the /usr/bin/time file
get_kv() { awk -v K="$1" '{for(i=1;i<=NF;i++){split($i,a,"="); if(a[1]==K){print a[2]; exit}}}' "$2"; }

# median of a list of numbers (still works with REPS=1)
median() {
  if [ "$#" -eq 0 ]; then echo "NaN"; return; fi
  printf "%s\n" "$@" | sort -n | awk '{a[NR]=$1} END{ if(NR==0)print "NaN"; else if(NR%2)print a[(NR+1)/2]; else print (a[NR/2]+a[NR/2+1])/2 }'
}

for SPEC in "${SPECTRA[@]}"; do
  for DIAM in "${DIAMS[@]}"; do

    # Cutoff = radius = diameter / 2
    case "$DIAM" in
      10) CUTOFF="5.0" ;;
      5)  CUTOFF="2.5" ;;
      1)  CUTOFF="0.5" ;;
      *)  CUTOFF="2.5" ;; # fallback
    esac

    COMBO_DIR="$OUTDIR/spec_${SPEC}_D${DIAM}cm_H${HIST}_T${T}"
    mkdir -p "$COMBO_DIR"

    TMP="$COMBO_DIR/macro_${SPEC}_D${DIAM}cm_H${HIST}_T${T}.txt"

    # Build temp macro with overrides
    awk -v H="$HIST" -v T="$T" -v SPEC="$SPEC" -v CUTOFF="$CUTOFF" -v RUNBASE="$COMBO_DIR" '
      BEGIN{
        nt=qt=gv=hq=0;
        dvs=0; dws=0; cx=0; cy=0;
        dg=0; ps=0; vx=0; vy=0; vz=0; ax=0; ay=0; az=0;
      }

      /^i:Ts\/NumberOfThreads/ {
        printf "i:Ts/NumberOfThreads = %d\n", T; nt=1; next
      }
      /^b:Ts\/UseQt/ {
        print  "b:Ts/UseQt = \"False\""; qt=1; next
      }
      /^b:Gr\/View\/Active/ {
        print  "b:Gr/View/Active = \"False\""; gv=1; next
      }
      /^i:So\/Beam\/NumberOfHistoriesInRun/ {
        printf "i:So/Beam/NumberOfHistoriesInRun = %d\n", H; hq=1; next
      }

      # --- Beam spectrum values ---
      /^dv:So\/Beam\/BeamEnergySpectrumValues/ {
        if (SPEC == "6MV") {
          print "dv:So/Beam/BeamEnergySpectrumValues  = 23 0.1 0.25 0.50 0.75 1.00 1.25 1.50 1.75 2.00 2.25 2.50 2.75 3.00 3.25 3.50 3.75 4.00 4.25 4.50 4.75 5.00 5.25 5.50 MeV";
        } else {
          print "dv:So/Beam/BeamEnergySpectrumValues  = 43 0.1 0.25 0.50 0.75 1.00 1.25 1.50 1.75 2.00 2.25 2.50 2.75 3.00 3.25 3.50 3.75 4.00 4.25 4.50 4.75 5.00 5.25 5.50 5.75 6.00 6.25 6.5 6.75 7.0 7.25 7.5 7.75 8.0 8.25 8.5 8.75 9.0 9.25 9.5 9.75 10.0 10.25 10.5 MeV";
        }
        dvs=1; next
      }

      # --- Beam spectrum weights ---
      /^uv:So\/Beam\/BeamEnergySpectrumWeights/ {
        if (SPEC == "6MV") {
          print "uv:So/Beam/BeamEnergySpectrumWeights = 23 .82 8.11 9.81 7.80 6.5 5.42 4.60 3.85 3.25 2.78 2.37 2.04 1.74 1.49 1.29 1.12 0.949 0.80 .662 .509 .373 .209 .0";
        } else {
          print "uv:So/Beam/BeamEnergySpectrumWeights = 43 2.85 8.21 12.21 10.18 9.87 9.33 8.64 7.96 7.25 6.61 5.98 5.44 4.94 4.49 4.10 3.74 3.40 3.12 2.85 2.63 2.41 2.22 2.06 1.91 1.73 1.61 1.49 1.36 1.26 1.15 1.05 0.98 0.87 0.80 0.71 0.62 0.55 0.46 0.38 0.29 0.21 0.12 0";
        }
        dws=1; next
      }

      # --- Beam position cutoffs (from beam diameter) ---
      /^d:So\/Beam\/BeamPositionCutoffX/ {
        printf "d:So/Beam/BeamPositionCutoffX        = %s cm\n", CUTOFF; cx=1; next
      }
      /^d:So\/Beam\/BeamPositionCutoffY/ {
        printf "d:So/Beam/BeamPositionCutoffY        = %s cm\n", CUTOFF; cy=1; next
      }

      # --- Scorer output files (override to per-run folder) ---
      /^s:Sc\/DoseGrid\/OutputFile/ {
        printf "s:Sc/DoseGrid/OutputFile                = \"%s/DoseGrid\"\n", RUNBASE; dg=1; next
      }
      /^s:Sc\/PS\/OutputFile/ {
        printf "s:Sc/PS/OutputFile                      = \"%s/PS\"\n", RUNBASE; ps=1; next
      }
      /^s:Sc\/velWeightCurrElX\/OutputFile/ {
        printf "s:Sc/velWeightCurrElX/OutputFile              = \"%s/velWeightCurrElX\"\n", RUNBASE; vx=1; next
      }
      /^s:Sc\/velWeightCurrElY\/OutputFile/ {
        printf "s:Sc/velWeightCurrElY/OutputFile              = \"%s/velWeightCurrElY\"\n", RUNBASE; vy=1; next
      }
      /^s:Sc\/velWeightCurrElZ\/OutputFile/ {
        printf "s:Sc/velWeightCurrElZ/OutputFile              = \"%s/velWeightCurrElZ\"\n", RUNBASE; vz=1; next
      }
      /^s:Sc\/angCurrElX\/OutputFile/ {
        printf "s:Sc/angCurrElX/OutputFile             = \"%s/angCurrElX\"\n", RUNBASE; ax=1; next
      }
      /^s:Sc\/angCurrElY\/OutputFile/ {
        printf "s:Sc/angCurrElY/OutputFile             = \"%s/angCurrElY\"\n", RUNBASE; ay=1; next
      }
      /^s:Sc\/angCurrElZ\/OutputFile/ {
        printf "s:Sc/angCurrElZ/OutputFile             = \"%s/angCurrElZ\"\n", RUNBASE; az=1; next
      }
      /^s:Sc\/distCurrElX\/OutputFile/ {
        printf "s:Sc/distCurrElX/OutputFile             = \"%s/distCurrElX\"\n", RUNBASE; ax=1; next
      }
      /^s:Sc\/distCurrElY\/OutputFile/ {
        printf "s:Sc/distCurrElY/OutputFile             = \"%s/distCurrElY\"\n", RUNBASE; ay=1; next
      }
      /^s:Sc\/distCurrElZ\/OutputFile/ {
        printf "s:Sc/distCurrElZ/OutputFile             = \"%s/distCurrElZ\"\n", RUNBASE; az=1; next
      }

      { print }

      END{
        if(!nt) printf "i:Ts/NumberOfThreads = %d\n", T;
        if(!qt) print  "b:Ts/UseQt = \"False\"";
        if(!gv) print  "b:Gr/View/Active = \"False\"";
        if(!hq) printf "i:So/Beam/NumberOfHistoriesInRun = %d\n", H;

        if(!dvs) {
          if (SPEC == "6MV")
            print "dv:So/Beam/BeamEnergySpectrumValues  = 23 0.1 0.25 0.50 0.75 1.00 1.25 1.50 1.75 2.00 2.25 2.50 2.75 3.00 3.25 3.50 3.75 4.00 4.25 4.50 4.75 5.00 5.25 5.50 MeV";
          else
            print "dv:So/Beam/BeamEnergySpectrumValues  = 43 0.1 0.25 0.50 0.75 1.00 1.25 1.50 1.75 2.00 2.25 2.50 2.75 3.00 3.25 3.50 3.75 4.00 4.25 4.50 4.75 5.00 5.25 5.50 5.75 6.00 6.25 6.5 6.75 7.0 7.25 7.5 7.75 8.0 8.25 8.5 8.75 9.0 9.25 9.5 9.75 10.0 10.25 10.5 MeV";
        }
        if(!dws) {
          if (SPEC == "6MV")
            print "uv:So/Beam/BeamEnergySpectrumWeights = 23 .82 8.11 9.81 7.80 6.5 5.42 4.60 3.85 3.25 2.78 2.37 2.04 1.74 1.49 1.29 1.12 0.949 0.80 .662 .509 .373 .209 .0";
          else
            print "uv:So/Beam/BeamEnergySpectrumWeights = 43 2.85 8.21 12.21 10.18 9.87 9.33 8.64 7.96 7.25 6.61 5.98 5.44 4.94 4.49 4.10 3.74 3.40 3.12 2.85 2.63 2.41 2.22 2.06 1.91 1.73 1.61 1.49 1.36 1.26 1.15 1.05 0.98 0.87 0.80 0.71 0.62 0.55 0.46 0.38 0.29 0.21 0.12 0";
        }
        if(!cx) printf "d:So/Beam/BeamPositionCutoffX        = %s cm\n", CUTOFF;
        if(!cy) printf "d:So/Beam/BeamPositionCutoffY        = %s cm\n", CUTOFF;

        if(!dg) printf "s:Sc/DoseGrid/OutputFile                = \"%s/DoseGrid\"\n", RUNBASE;
        if(!ps) printf "s:Sc/PS/OutputFile                      = \"%s/PS\"\n", RUNBASE;
        if(!vx) printf "s:Sc/velWeightCurrElX/OutputFile              = \"%s/velWeightCurrElX\"\n", RUNBASE;
        if(!vy) printf "s:Sc/velWeightCurrElY/OutputFile              = \"%s/velWeightCurrElY\"\n", RUNBASE;
        if(!vz) printf "s:Sc/velWeightCurrElZ/OutputFile              = \"%s/velWeightCurrElZ\"\n", RUNBASE;
        if(!ax) printf "s:Sc/angCurrElX/OutputFile             = \"%s/angCurrElX\"\n", RUNBASE;
        if(!ay) printf "s:Sc/angCurrElY/OutputFile             = \"%s/angCurrElY\"\n", RUNBASE;
        if(!az) printf "s:Sc/angCurrElZ/OutputFile             = \"%s/angCurrElZ\"\n", RUNBASE;
        if(!ax) printf "s:Sc/distCurrElX/OutputFile             = \"%s/distCurrElX\"\n", RUNBASE;
        if(!ay) printf "s:Sc/distCurrElY/OutputFile             = \"%s/distCurrElY\"\n", RUNBASE;
        if(!az) printf "s:Sc/distCurrElZ/OutputFile             = \"%s/distCurrElZ\"\n", RUNBASE;
      }
    ' "$BASE" > "$TMP"

    # Repeated runs (REPS=1 here)
    walls=(); users=(); syss=(); rsss=(); last_log=""
    for r in $(seq 1 $REPS); do
      TIMEFILE="$COMBO_DIR/time_r${r}.txt"
      LOG="$COMBO_DIR/run_r${r}.log"

      /usr/bin/time -f "wall=%e user=%U sys=%S rss=%M" -o "$TIMEFILE" \
        "$TOPAS_BIN" "$TMP" > "$LOG" 2>&1

      if [[ -s "$TIMEFILE" ]]; then
        w=$(get_kv wall "$TIMEFILE"); u=$(get_kv user "$TIMEFILE")
        s=$(get_kv sys "$TIMEFILE");  rkb=$(get_kv rss "$TIMEFILE")
        walls+=("$w"); users+=("$u"); syss+=("$s"); rsss+=("$rkb")
        printf "rep=%d spec=%-4s D=%-3scm T=%-2s H=%-8s wall=%s\n" "$r" "$SPEC" "$DIAM" "$T" "$HIST" "$w"
        last_log="$LOG"
      else
        echo "WARN: no timing in $TIMEFILE"
      fi
    done

    # Aggregate (median, but with REPS=1 == that value)
    wall=$(median "${walls[@]}")
    user=$(median "${users[@]}")
    sys=$(median  "${syss[@]}")
    rss=$(median  "${rsss[@]}")

    eps=$(awk -v H="$HIST" -v W="$wall" 'BEGIN{ if (W+0>0) printf "%.6f", H/(W+0); else print 0 }')

    echo "$SPEC,$DIAM,$HIST,$T,$wall,$user,$sys,$rss,$eps,$last_log" >> "$CSV"
    printf "OK  spec=%-4s D=%-3scm T=%-2s H=%-8s wall_med=%-8s eps=%s\n" "$SPEC" "$DIAM" "$T" "$HIST" "$wall" "$eps"

    rm -f "$COMBO_DIR"/time_r*.txt

  done
done

echo "Done -> $CSV"
# ========================= End of main sweep =========================
