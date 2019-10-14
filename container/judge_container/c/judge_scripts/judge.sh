for input_file in `\find /judge/tests/ -name '*.in'`; do
    (time --format="%e %S %U %P %K %x %C" timeout $1 /judge/a.out < ${input_file} > ${input_file%.*}.out) 2>${input_file%.*}.result
done