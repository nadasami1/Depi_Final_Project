import os
os.environ['JAVA_HOME'] = 'C:/Program Files/Java/jdk-27.0.1.0.3'

import traceback
import pandas as pd
import tabula

base = 'C:/Users/GOLDEN TECH/Downloads/AquaAgri_Egypt/Data'
raw = base + '/raw/CAPMAS'
#out = base + '/processed/CAPMAS/clean'
#rev = base + '/processed/CAPMAS/review'
out = base + '/processed/CAPMAS/clean_v2' 
rev = base + '/processed/CAPMAS/review_v2'
os.makedirs(out, exist_ok=True)
os.makedirs(rev, exist_ok=True)

pg = {
    2016: {6: 27, 8: 29, 10: 31, 12: 33, 21: 43},
    2017: {6: 27, 8: 29, 10: 31, 12: 33, 21: 43},
    2018: {6: 27, 8: 29, 10: 31, 12: 33, 21: 43},
    2019: {6: 29, 8: 31, 10: 33, 12: 35, 21: 45},
    2020: {6: 28, 8: 30, 10: 32, 12: 34, 21: 44},
}

tabs = {
    6: ('winter', ['wheat', 'barley', 'beans', 'lentils', 'fenugreek', 'chickpeas',
                   'lupine', 'sugar_beet', 'alfalfa_sustained', 'alfalfa_forestation',
                   'flax', 'onions', 'garlic', 'medical_aromatic', 'others',
                   'vegetables', 'total']),
    8: ('summer', ['cotton', 'sugar_cane', 'maize', 'sorghum', 'rice', 'onions',
                   'peanuts', 'soybean', 'sesame', 'sunflower', 'green_fodder',
                   'medical_aromatic', 'others', 'vegetables', 'total']),
    10: ('nile', ['maize', 'sorghum', 'onions', 'soybean', 'sesame', 'sunflower',
                  'green_fodder', 'medical_aromatic', 'vegetables', 'total']),
    12: ('fruit', ['deciduous_feddan', 'deciduous_water', 'permanent_feddan',
                   'permanent_water', 'total_feddan', 'total_water']),
    21: ('all_seasons', ['winter_canals', 'winter_aswan', 'summer_canals', 'summer_aswan',
                         'nile_canals', 'nile_aswan', 'fruit_canals', 'fruit_aswan',
                         'total_canals', 'total_aswan']),
}

year_cols = {
    (2017, 10): ['maize', 'sorghum', 'onions', 'peanuts', 'soybean', 'sesame', 'sunflower',
                 'green_fodder', 'medical_aromatic', 'vegetables', 'total'],
    (2019, 10): ['maize', 'sorghum', 'onions', 'sesame', 'sunflower',
                 'medical_aromatic', 'green_fodder', 'vegetables', 'total'],
    (2020, 8): ['cotton', 'sugar_cane', 'maize', 'sorghum', 'rice', 'onions', 'peanuts',
                'soybean', 'sesame', 'sunflower', 'alfalfa_crop', 'green_fodder',
                'medical_aromatic', 'others', 'vegetables', 'total'],
}

fixes = [('kafr', 'Kafr El Sheikh'), ('sheikh', 'Kafr El Sheikh'),
         ('beni', 'Beni Suef'), ('bani', 'Beni Suef'), ('sweif', 'Beni Suef'),
         ('qal', 'Qalyubia'), ('beh', 'Beheira'),
         ('menia', 'Minya'), ('minya', 'Minya'),
         ('menouf', 'Menoufia'), ('monouf', 'Menoufia'),
         ('sohag', 'Sohag'), ('suhag', 'Sohag'),
         ('assuit', 'Assiut'), ('asyut', 'Assiut'), ('gharb', 'Gharbia')]


def get_raw(year, tbl):
    f = f'{raw}/capmas_irrigation_{year}.pdf'
    if not os.path.exists(f):
        raise FileNotFoundError(f)

    t = tabula.read_pdf(f, pages=pg[year][tbl], lattice=False,
                        multiple_tables=True, pandas_options={'header': None})
    if not t:
        raise ValueError('no table found')
    return pd.concat(t, ignore_index=True)


def chk_num(x):
    return x in ('-', '=') or x.replace('.', '', 1).isdecimal()


def to_float(x):
    if x == '-':
        return 0.0
    if x == '=':
        return None
    return float(x)


def clean_rows(df, cols):
    good, bad = [], []
    for _, r in df.iterrows():
        cells = [str(c) for c in r if pd.notna(c)]
        toks = ' '.join(cells).replace(',', '').split()

        nums = [t for t in toks if chk_num(t)]
        txt = [t for t in toks if not chk_num(t)]

        if len(nums) < 3 or not txt:
            continue

        if len(nums) != len(cols):
            bad.append({'row': ' '.join(toks), 'num_count': len(nums)})
            continue

        vals = [to_float(t) for t in nums]
        mx = max((v for v in vals if v is not None), default=0)

        # the total is the biggest number, some rows come out reversed
        if vals[0] == mx and vals[-1] != mx:
            vals.reverse()

        ar = ' '.join(w for w in txt if not w.isascii())
        en = ' '.join(w for w in txt if w.isascii())
        good.append([ar, en] + vals)

    c = ['governorate_ar', 'governorate_en'] + cols
    return pd.DataFrame(good, columns=c), pd.DataFrame(bad)


def get_type(ar, en):
    e = en.lower().replace(' ', '')
    if 'total.g' in e or 'g.total' in e or 'العام' in ar:
        return 'grand_total'
    if 'egypt' in e or 'total' in e or 'جمالى' in ar:
        return 'subtotal'
    return 'governorate'


def fix_gov(en, ar):
    if not en and 'بور سعيد' in ar:
        return 'Port Said'
    low = en.lower()
    for k, v in fixes:
        if k in low:
            return v
    return en.strip()


def do_check(df, cols):
    errs = []
    govs = df[df['row_type'] == 'governorate']
    grand = df[df['row_type'] == 'grand_total']

    if len(govs) < 15:
        errs.append(f'got {len(govs)} govs')

    if len(grand) != 1:
        errs.append(f'got {len(grand)} grand totals')
    else:
        last = cols[-1]
        target = grand[last].iloc[0]
        got = govs[last].sum()
        if target and abs(got - target) / target > 0.01:
            errs.append(f'{last} sum mismatch')

    if govs['governorate_en'].duplicated().any():
        errs.append('dup gov names')

    return errs


def build_table(year, tbl):
    s, cols = tabs[tbl]
    cols = year_cols.get((year, tbl), cols)
    df, bad = clean_rows(get_raw(year, tbl), cols)

    df['row_type'] = [get_type(a, e) for a, e in zip(df['governorate_ar'], df['governorate_en'])]
    df['governorate_en'] = [fix_gov(e, a) if t == 'governorate' else e.strip()
                            for e, a, t in zip(df['governorate_en'], df['governorate_ar'], df['row_type'])]

    df['year'] = year
    df['table_no'] = tbl
    df['season'] = s
    df['source'] = 'CAPMAS'

    errs = do_check(df, cols)
    if len(bad):
        errs.append(f'{len(bad)} bad rows')

    df['qc'] = 'review' if errs else 'ok'
    return df, bad, errs


def main():
    all_dfs, logs = [], []
    keep = ['year', 'table_no', 'season', 'source', 'governorate_ar',
            'governorate_en', 'row_type', 'qc']

    for y in pg:
        for t in pg[y]:
            s = tabs[t][0]
            print(y, s)

            try:
                df, bad, errs = build_table(y, t)
            except Exception as e:
                traceback.print_exc()
                logs.append({'year': y, 'table': t, 'season': s, 'rows': 0,
                             'status': 'failed', 'issues': str(e)})
                continue

            df.to_csv(f'{out}/capmas_{y}_{s}_wide.csv', index=False, encoding='utf-8-sig')

            if len(bad):
                bad.to_csv(f'{rev}/bad_rows_{y}_{s}.csv', index=False, encoding='utf-8-sig')

            long = df.melt(id_vars=keep, var_name='variable', value_name='value')
            long['unit'] = ['feddan' if v.endswith('_feddan') else 'thousand_m3'
                            for v in long['variable']]
            all_dfs.append(long)

            stat = 'review' if errs else 'ok'
            logs.append({'year': y, 'table': t, 'season': s, 'rows': len(df),
                         'status': stat, 'issues': '; '.join(errs)})
            print('  ->', stat, errs)

    if all_dfs:
        pd.concat(all_dfs, ignore_index=True).to_csv(
            f'{out}/capmas_all_tables_long.csv', index=False, encoding='utf-8-sig')

    log_df = pd.DataFrame(logs)
    log_df.to_csv(f'{out}/capmas_quality_log.csv', index=False, encoding='utf-8-sig')
    print(log_df.to_string())


if __name__ == '__main__':
    main()