
import os
import re
from glob import glob
import subprocess
import textwrap
from functools import partial

import pandas as pd
from invoke import task
from docstamp.pdf_utils import merge_pdfs

templates_dir = os.path.join(os.path.dirname(__file__), 'templates')

ROLES = ['crew',
         'speaker',
         'participant']

USERS_FILE = 'tito.csv'


def get_userrole_filepath(users_file, role):
    return os.path.basename(users_file).split('.')[0] + '_' + role + '.csv'


COLUMNS = [
    'Number',
    'Ticket',
    'Ticket Full Name',
    'Ticket First Name',
    'Ticket Last Name',
    'Ticket Email',
    'Ticket Reference',
    'Ticket Company Name',
    'Badge information',
    'Tags'
]


FILTER_TICKETS = {
    'Ticket': ('Business', 'Regular', 'Student')
}


MAXLENGTHS = {
    'Ticket First Name':   20,
    'Ticket Last Name':    20,
    'Ticket Company Name': 35,
}


COLS_WITH_2_LINES = [
    'Ticket Company Name'
]


def badge_template_file(role):
    return '{}.svg'.format(role)


def create_badge_faces(pdf_filepath):
    """ duplicate the given pdf, save it in a file with '-joined.pdf' suffix
    and return the new filepath.
    """
    return merge_pdfs([pdf_filepath] * 2, pdf_filepath.replace('.pdf', '-joined.pdf'))


def split_in_two(string, separator='@', max_length=30):
    """ Split `string` in two strings of maximum length `max_length`.
    The rest is thrown away, sorry.
    This function looks for a `separator` before `max_length`,
    if it is found, it splits the string by the position
    of the `separator` instead of `max_length`.

    Return
    ------
    split: 2-tuple of str
    """
    if not string or string is None or pd.isnull(string):
        return '', ''

    if separator in string:
        wrap = textwrap.wrap(string, width=max_length)
        if len(wrap) >= 2:
            idx = string.find(separator)
            wrap11, wrap12 = split_in_two(string[0:idx].strip(),  max_length=max_length)
            wrap21, wrap22 = split_in_two(string[idx+1:].strip(), max_length=max_length)
            return wrap11 + ' {}'.format(separator), wrap21

    wrap = textwrap.wrap(string, width=max_length)
    if len(wrap) >= 2:
        return wrap[0], wrap[1]

    return wrap[0], ''


def _wrap_colum_values(df, col_name, max_length):
    """ Will split each string value in df[col_name] to two values.
    These values will be put in col_name + "1" and col_name + "2"
    and df[col_name] will be removed.
    """
    split_values = partial(split_in_two, max_length=max_length)

    split = df[col_name].map(split_values)

    if col_name in COLS_WITH_2_LINES:
        df[col_name + '1'] = [val1 for val1, val2 in split]
        df[col_name + '2'] = [val2 for val1, val2 in split]
        del df[col_name]
    else:
        df[col_name] = [val1 for val1, val2 in split]


def wrap_cell_contents(df, field_maxlength):
    """
    """
    for field, maxlength in field_maxlength.items():
        _wrap_colum_values(df, field, maxlength)

    return df


def _pdf_to_cmyk(input_file: str, output_file: str):
    cmd = 'gs -dSAFER -dBATCH -dNOPAUSE -dNOCACHE -sDEVICE=pdfwrite ' \
        '-sColorConversionStrategy=CMYK ' \
        '-dProcessColorModel=/DeviceCMYK ' \
        '-sOutputFile="{}" "{}"'.format(output_file, input_file)
    print('Calling {}'.format(cmd))
    subprocess.call(cmd, shell='True')


def create_badge_set(input_file, outdir, template_file):
    cmd = 'docstamp create --unicode_support -i "{}" -t "{}" -f "Ticket_Reference" -d pdf -o "{}"'.format(
        input_file,
        template_file,
        outdir
    )
    print('Calling {}'.format(cmd))
    subprocess.call(cmd, shell='True')


def empty_data_for_blank_badge(role: str):
    empty_data = {
        'Number': [1],
        'Ticket_Full_Name': [''],
        'Ticket_First_Name': [''],
        'Ticket_Last_Name': [''],
        'Ticket_Email': ['{}@pyconweb'.format(role)],
        'Ticket_Company_Name': [''],
        'Ticket_Reference': ['blank'],
        'Badge information': [''],
        'Tags': [role],
    }
    return empty_data


@task
def create_empty_badges(ctx, outdir='stamped'):
    for role in ROLES:
        empty_badges_csv_file = 'empty_badge_for_{}.csv'.format(role)
        print('Creating empty data csv file "{}".'.format(empty_badges_csv_file))
        empty_data = empty_data_for_blank_badge(role)
        empty_df = pd.DataFrame.from_dict(empty_data)
        empty_df.to_csv(empty_badges_csv_file, index=False)

        template_file = os.path.join('templates', badge_template_file(role))
        create_badge_set(input_file=empty_badges_csv_file, template_file=template_file, outdir=outdir)
        os.remove(empty_badges_csv_file)


@task
def split_users_csv(ctx, users_file=USERS_FILE):
    df = pd.read_csv(users_file)

    for col, values in FILTER_TICKETS.items():
        df = df.loc[df[col].isin(values)]

    df.columns = [col.replace(' ', '_') for col in df.columns]
    column_names = [col.replace(' ', '_') for col in COLUMNS]
    col_maxlengths = {col.replace(' ', '_'):length for col, length in MAXLENGTHS.items()}

    # Set Tags to 'participant'
    df.loc[pd.isnull(df.Tags), 'Tags'] = 'participant'
    df.loc[
        (df.Tags == 'participant') & (df.Ticket.str.contains('Late')),
        'Tags'
    ] = 'participant'

    # Set Tags to 'crew'
    df.loc[
        (df.Tags.str.contains('crew')) & (df.Tags.str.contains('organizer')),
        'Tags'
    ] = 'crew'

    # Merge Badge_information into Ticket_Company_Name if null
    df.loc[
        pd.isnull(df.Ticket_Company_Name), 'Ticket_Company_Name'
    ] = df.loc[pd.isnull(df.Ticket_Company_Name), 'Badge_information']

    df = df[column_names]
    df = wrap_cell_contents(df, field_maxlength=col_maxlengths)

    for role in ROLES:
        role_df = df[df.Tags.str.contains(role)]
        output_file = get_userrole_filepath(users_file, role)
        role_df.to_csv(output_file, index=False)


@task
def create_badges_for(ctx, role, users_file=USERS_FILE, outdir='stamped'):
    input_file = get_userrole_filepath(users_file, role)
    template_file = os.path.join('templates', badge_template_file(role))
    create_badge_set(input_file=input_file, outdir=outdir, template_file=template_file)


@task
def make_all_badges(ctx, users_file=USERS_FILE, outdir='stamped'):
    for role in ROLES:
        create_badges_for(ctx, role, users_file=users_file, outdir=outdir)


@task
def convert_badges_to_cmyk(ctx, stamped_dir='stamped', cleanup=True):
    pdf_files = glob(os.path.join(stamped_dir, '*.pdf'))
    for pdf_filepath in pdf_files:
        if pdf_filepath.endswith('joined.pdf'):
            continue
        _pdf_to_cmyk(pdf_filepath, pdf_filepath.replace('.pdf', '_cmyk.pdf'))

        if cleanup:
            os.remove(pdf_filepath)


@task
def make_badge_faces(ctx, stamped_dir='stamped', cleanup=True):
    pdf_files = glob(os.path.join(stamped_dir, '*.pdf'))
    for pdf_filepath in pdf_files:
        if pdf_filepath.endswith('joined.pdf'):
            continue

        pdf_pair_file = create_badge_faces(pdf_filepath)
        print('Created {}'.format(pdf_pair_file))
        if cleanup:
            os.remove(pdf_filepath)


@task
def escape_csv(ctx, input_file):
    with open(input_file, 'r') as csvfile:
        data = csvfile.read()
    escaped_data = re.sub(r'&(?!amp)', '&amp;', data)
    with open(input_file, 'w') as csvfile:
        pass
        csvfile.write(escaped_data)


@task
def all(ctx, input_file=USERS_FILE, outdir='stamped'):
    escape_csv(ctx, input_file=input_file)
    split_users_csv(ctx, users_file=input_file)
    make_all_badges(ctx, users_file=input_file, outdir=outdir)
    convert_badges_to_cmyk(ctx, stamped_dir=outdir)
    make_badge_faces(ctx, stamped_dir=outdir, cleanup=True)

    create_empty_badges(ctx, outdir='blank')
    convert_badges_to_cmyk(ctx, stamped_dir='blank')
    make_badge_faces(ctx, stamped_dir='blank', cleanup=True)
