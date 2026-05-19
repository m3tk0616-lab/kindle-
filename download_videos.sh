#!/bin/bash

OUTPUT_DIR="/home/user/kindle-/videos"
mkdir -p "$OUTPUT_DIR"

declare -A VIDEOS=(
  ["導入1(TOKAI式サーチ)day2"]="https://youtu.be/tMiNts3eaxI"
  ["導入2(TOKAI式サーチ)day2"]="https://youtu.be/sj7pHP8Ybs8"
  ["導入3(デンバー)day2"]="https://youtu.be/lmgpZ3z0Krg"
  ["アップバーピーday2"]="https://youtu.be/vzOR3-MGLes"
  ["VEISデンバー1day2"]="https://youtu.be/9WsxXNLb92U"
  ["ベイルアウト1day2"]="https://youtu.be/ZwNw8DXZQYQ"
  ["ベイルアウト2day2"]="https://youtu.be/dPPa1NbLcyY"
  ["サーチ1day2"]="https://youtu.be/64elf63maPY"
  ["サーチ2day2"]="https://youtu.be/6c-QHhll3mY"
  ["FFS3階～2階ベイルアウト1day2"]="https://youtu.be/q0ebHGBe37k"
  ["セブンティーンday2"]="https://youtu.be/B9dqPXc0IOY"
  ["ベイルアウト3day2"]="https://youtu.be/A8Em8mRsQJ0"
  ["サーチ3day2"]="https://youtu.be/6RQUAo6-B44"
  ["FFS3階～ベイルアウト2day2"]="https://youtu.be/1XpFGHvZb3o"
  ["サーチ4day2"]="https://youtu.be/jTeCEgo7Tfo"
  ["FFS3階～2階ベイルアウト4day2"]="https://youtu.be/eE_jBdMslfE"
  ["Heavy Rescue Japan機材デモ1day2"]="https://youtu.be/S_XDSLKjQQs"
  ["Heavy Rescue Japan機材デモ2day2"]="https://youtu.be/pMzlJstN1p4"
  ["Heavy Rescue Japan機材デモ3day2"]="https://youtu.be/18pW1mNdIyE"
  ["ラージエリア説明day2"]="https://youtu.be/usrjxepjIo4"
  ["ラージエリア1day2"]="https://youtu.be/Is6eTg5wcCI"
  ["ラージエリア2day2"]="https://youtu.be/MygcjFdlauU"
  ["想定1-1"]="https://youtu.be/gsCusW_6_hg"
  ["想定1-2"]="https://youtu.be/PdxDOSQSyQM"
  ["想定2-1"]="https://youtu.be/rGBxIfDEN-s"
  ["想定2-2"]="https://youtu.be/t6Z9rqtDSec"
  ["想定2-3"]="https://youtu.be/zDOwKm_XpPs"
  ["想定2-4"]="https://youtu.be/De1YWre99iM"
  ["まとめ"]="https://youtu.be/LZKKQy-iWPY"
)

for TITLE in "${!VIDEOS[@]}"; do
  URL="${VIDEOS[$TITLE]}"
  echo "Downloading: $TITLE ($URL)"
  yt-dlp -o "$OUTPUT_DIR/%(title)s.%(ext)s" "$URL"
done

echo "All downloads complete. Files saved to $OUTPUT_DIR"
