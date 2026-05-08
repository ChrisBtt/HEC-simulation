#!/usr/bin/env bash

# To run:
# chmod +x beam_sweep.sh
# ./beam_sweep.sh

set -u
export LC_ALL=C

TOPAS_BIN="/root/shellScripts/topas"  # adjust Topas path here
BASE="/mnt/e/Christoph/applications/hec-dose-distribution/TOPAS_macros/motor_servo/simulation.txt" # base macro
OUTDIR="/mnt/e/Christoph/applications/hec-dose-distribution/TOPAS_simulation_data/motor_servo"
mkdir -p "$OUTDIR"

[[ -x "$TOPAS_BIN" ]] || { echo "No topas at $TOPAS_BIN"; exit 1; }
[[ -f "$BASE" ]]      || { echo "No base macro at $BASE"; exit 1; }

# ========================= Main settings =========================
HIST=1000000        # single number of histories
T=24                # single number of threads
REPS=1              # single repetition

# beam energies and diameters
SHIFTS=(-4 -3.5 -3 -2.5 -2 -1.5 -1 -0.5 0 0.5 1 1.5 2 2.5 3 3.5 4) # cm
FIELDS=(0.5)      # cm

CSV="$OUTDIR/results.csv"
echo "field,shift_cm,hist,threads,wall_s,user_s,sys_s,rss_kb,eps,log" > "$CSV"
# wall: overall runtime (user+sys + overhead) in seconds 
# user: CPU time in user mode
# sys: CPU time in kernel mode
# rss: max resident set size (memory), in kilobytes
# eps: events per second = hist / wall

# key=value extractor for the /usr/bin/time file
get_kv() { awk -v K="$1" '{for(i=1;i<=NF;i++){split($i,a,"="); if(a[1]==K){print a[2]; exit}}}' "$2"; }

# median of a list of numbers (still works with REPS=1)
median() {
  if [ "$#" -eq 0 ]; then echo "NaN"; return; fi
  printf "%s\n" "$@" | sort -n | awk '{a[NR]=$1} END{ if(NR==0)print "NaN"; else if(NR%2)print a[(NR+1)/2]; else print (a[NR/2]+a[NR/2+1])/2 }'
}

for SHIFT in "${SHIFTS[@]}"; do
  for FIELD in "${FIELDS[@]}"; do

    # Cutoff = radius = diameter / 2
    case "$FIELD" in
      7) CUTOFF="3.5" ;;
      1)  CUTOFF="0.5" ;;
      0.5)  CUTOFF="0.25" ;;
      *)  CUTOFF="2.5" ;; # fallback
    esac

    COMBO_DIR="$OUTDIR/F7x${FIELD}_S${SHIFT}"
    mkdir -p "$COMBO_DIR"

    TMP="$COMBO_DIR/macro_F7x${FIELD}_S${SHIFT}.txt"

    # Build temp macro with overrides
    awk -v T="$T" -v SHIFT="$SHIFT" -v CUTOFF="$CUTOFF" -v RUNBASE="$COMBO_DIR" -v HIST="$HIST" '
      BEGIN{
        nt=qt=gv=hq=0;
        cx=0; tz=0;
        dg=0; ps=0; vx=0; vy=0; vz=0;
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
        printf "i:So/Beam/NumberOfHistoriesInRun = %d\n", HIST; hq=1; next
      }

      # --- Beam position cutoffs (from beam diameter) ---
      /^d:So\/Beam\/BeamPositionCutoffX/ {
        printf "d:So/Beam/BeamPositionCutoffX        = %s cm\n", CUTOFF; cx=1; next
      }

      # --- Wodden phantom translation (from motor motion) ---
      /^d:Ge\/LungTumor\/TransZ/ {
        printf "d:Ge/LungTumor/TransZ   = %s cm\n", SHIFT; tz=1; next
      }

      # --- Scorer output files (override to per-run folder) ---
      /^s:Sc\/DoseGrid\/OutputFile/ {
        printf "s:Sc/DoseGrid/OutputFile                = \"%s/DoseGrid\"\n", RUNBASE; dg=1; next
      }
      /^s:Sc\/PS\/OutputFile/ {
        printf "s:Sc/PS/OutputFile                      = \"%s/PS\"\n", RUNBASE; ps=1; next
      }
      /^s:Sc\/velCurrElX\/OutputFile/ {
        printf "s:Sc/velCurrElX/OutputFile              = \"%s/velCurrElX\"\n", RUNBASE; vx=1; next
      }
      /^s:Sc\/velCurrElY\/OutputFile/ {
        printf "s:Sc/velCurrElY/OutputFile              = \"%s/velCurrElY\"\n", RUNBASE; vy=1; next
      }
      /^s:Sc\/velCurrElZ\/OutputFile/ {
        printf "s:Sc/velCurrElZ/OutputFile              = \"%s/velCurrElZ\"\n", RUNBASE; vz=1; next
      }

      { print }

      END{
        if(!nt) printf "i:Ts/NumberOfThreads = %d\n", T;
        if(!qt) print  "b:Ts/UseQt = \"False\"";
        if(!gv) print  "b:Gr/View/Active = \"False\"";
        if(!hq) printf "i:So/Beam/NumberOfHistoriesInRun = %d\n", HIST;

        if(!cx) printf "d:So/Beam/BeamPositionCutoffX     = %s cm\n", CUTOFF;
        if(!tz) printf "d:Ge/LungTumor/TransZ             = %s cm\n", SHIFT;

        if(!dg) printf "s:Sc/DoseGrid/OutputFile                = \"%s/DoseGrid\"\n", RUNBASE;
        if(!ps) printf "s:Sc/PS/OutputFile                      = \"%s/PS\"\n", RUNBASE;
        if(!vx) printf "s:Sc/velCurrElX/OutputFile              = \"%s/velCurrElX\"\n", RUNBASE;
        if(!vy) printf "s:Sc/velCurrElY/OutputFile              = \"%s/velCurrElY\"\n", RUNBASE;
        if(!vz) printf "s:Sc/velCurrElZ/OutputFile              = \"%s/velCurrElZ\"\n", RUNBASE;
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
        printf "rep=%d shift=%-4s D=7x%-3scm T=%-2s H=%-8s wall=%s\n" "$r" "$SHIFT" "$FIELD" "$T" "$HIST" "$w"
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

    echo "7x$FIELD,$SHIFT,$HIST,$T,$wall,$user,$sys,$rss,$eps,$last_log" >> "$CSV"
    printf "OK  shift=%-4s D=7x%-3scm T=%-2s H=%-8s wall_med=%-8s eps=%s\n" "$SHIFT" "$FIELD" "$T" "$HIST" "$wall" "$eps"

    rm -f "$COMBO_DIR"/time_r*.txt

  done
done

echo "Done -> $CSV"
# ========================= End of main sweep =========================
