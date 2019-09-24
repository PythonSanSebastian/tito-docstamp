
import os
import re
import sys
import logging
import subprocess
import textwrap
from glob import glob
from typing import Tuple, List, Any
from functools import partial

import pandas as pd
from invoke import task
from docstamp.pdf_utils import merge_pdfs, pdf_to_cmyk

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def first_true(iterable, default='', pred=None):
    """Returns the first true value in the iterable.

    If no true value is found, returns *default*

    If *pred* is not None, returns the first item
    for which pred(item) is true.
    """
    # first_true([a,b,c], x) --> a or b or c or x
    # first_true([a,b], x, f) --> a if f(a) else b if f(b) else x
    return next(filter(pd.notna, iterable), default)


def join_strings(items: List[Any], symbol: str=''):
    return symbol.join(sorted({item for item in items if item}))


TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'euroscipy2019')

CONFERENCE_NAME = 'euroscipy'

ROLETAG_TEMPLATES = {
    'organizer': 'organizer',
    'keynote': 'keynote',
    'speaker+trainer': 'speaker+trainer',
    'conference+tutorials': 'conference_tutorials_participant',
    'speaker': 'speaker',
    'trainer': 'trainer',
    'conference': 'conference_participant',
    'tutorials': 'tutorials_participant',
}

USERS_FILE = 'tito.csv'

COLUMNS_RENAME = {
    'Number': 'number',
    'Ticket': 'ticket_type',
    'Ticket Full Name': 'full_name',
    'Ticket First Name': 'first_name',
    'Ticket Last Name': 'last_name',
    'Ticket Email': 'email',
    'Ticket Company Name': 'company',
    'Tagline': 'tagline',
    'Tags': 'tags',
    'Order Reference': 'order',
}

FILTER_TICKETS = {
    'Ticket': {
        'Financial Aid Ticket',
        'Bronze sponsorship',
        'Conference  (Wed/Thu) - Early Bird Business',
        'Conference  (Wed/Thu) - Early Bird Individual',
        'Conference  (Wed/Thu) - Early Bird Student',
        'Conference (Wed/Thu) - Business',
        'Conference (Wed/Thu) - Business Late',
        'Conference (Wed/Thu) - Individual',
        'Conference (Wed/Thu) - Individual Late',
        'Conference (Wed/Thu) - Organizer',
        'Conference (Wed/Thu) - Student',
        'Invited speaker',
        'Tutorials  (Mon/Tue) - Early Bird Business',
        'Tutorials  (Mon/Tue) - Early Bird Individual',
        'Tutorials  (Mon/Tue) - Early Bird Student',
        'Tutorials (Mon/Tue) - Business',
        'Tutorials (Mon/Tue) - Business Late',
        'Tutorials (Mon/Tue) - Individual',
        'Tutorials (Mon/Tue) - Individual Late',
        'Tutorials (Mon/Tue) - Organizer',
        'Tutorials (Mon/Tue) - Student',
    }
}

TICKET_TYPE_TEMPLATES = {
    'Financial Aid Ticket': 'conference+tutorials',
    'Bronze sponsorship': 'conference+tutorials',
    'Conference  (Wed/Thu) - Early Bird Business': 'conference',
    'Conference  (Wed/Thu) - Early Bird Individual': 'conference',
    'Conference  (Wed/Thu) - Early Bird Student': 'conference',
    'Conference (Wed/Thu) - Business': 'conference',
    'Conference (Wed/Thu) - Business Late': 'conference',
    'Conference (Wed/Thu) - Individual': 'conference',
    'Conference (Wed/Thu) - Individual Late': 'conference',
    'Conference (Wed/Thu) - Organizer': 'conference',
    'Conference (Wed/Thu) - Student': 'conference',
    'Invited speaker': 'keynote',
    'Tutorials  (Mon/Tue) - Early Bird Business': 'tutorials',
    'Tutorials  (Mon/Tue) - Early Bird Individual': 'tutorials',
    'Tutorials  (Mon/Tue) - Early Bird Student': 'tutorials',
    'Tutorials (Mon/Tue) - Business': 'tutorials',
    'Tutorials (Mon/Tue) - Business Late': 'tutorials',
    'Tutorials (Mon/Tue) - Individual': 'tutorials',
    'Tutorials (Mon/Tue) - Individual Late': 'tutorials',
    'Tutorials (Mon/Tue) - Organizer': 'tutorials',
    'Tutorials (Mon/Tue) - Student': 'tutorials',
}

GROUP_ROWS_BY = ['email']

GROUP_FUNC = {
    'order': '+'.join,
    'tags': lambda x: join_strings(x, '+'),
    'tagline': first_true,
    'full_name': first_true,
    'first_name': first_true,
    'last_name': first_true,
    'company': first_true,
    'ticket_type': first_true,
}

MAXLENGTHS = {
    'first_name': 20,
    'last_name': 20,
    'company': 35,
    'tagline': 35,
}

COLS_WITH_2_LINES = [
    'company',
    'tagline'
]


def add_suffix(input_file: str, suffix: str) -> str:
    extension = input_file.split('.')[-1]
    return input_file.replace(f'.{extension}', f'_{suffix}.{extension}')


def badge_template_file(role):
    return f'{ROLETAG_TEMPLATES[role]}.svg'


def create_badge_faces(pdf_filepath):
    """ duplicate the given pdf, save it in a file with '-joined.pdf' suffix
    and return the new filepath.
    """
    return merge_pdfs([pdf_filepath] * 2, pdf_filepath.replace('.pdf', '-joined.pdf'))


def split_in_two(string: str, max_length: int=30) -> Tuple[str, str]:
    """ Split `string` in two strings of maximum length `max_length`.
    The rest is thrown away, sorry.

    Return
    ------
    split: 2-tuple of str
    """
    if not string or pd.isnull(string):
        return '', ''

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
    else:
        df[col_name] = [val1 for val1, val2 in split]


def wrap_cell_contents(df, field_maxlength):
    """
    """
    for field, maxlength in field_maxlength.items():
        _wrap_colum_values(df, field, maxlength)
    return df


def create_badge_set(input_file, outdir, template_file):
    cmd = 'docstamp create --unicode_support '
    cmd += f'-i "{input_file}" '
    cmd += f'-t "{template_file}" '
    cmd += f'-f "email" '
    cmd += f'--dpi 72 '
    cmd += f'-o "{outdir}" '
    cmd += f'-d pdf'
    logger.info('Calling {}'.format(cmd))
    subprocess.call(cmd, shell='True')


def empty_data_for_blank_badge(role: str):
    empty_data = {value: [''] for value in COLUMNS_RENAME.values()}
    empty_data['email'] = f'{role}@euroscipy'
    return empty_data


@task
def create_empty_badges(ctx, outdir='stamped'):
    for role, template in ROLETAG_TEMPLATES.items():
        empty_badges_csv_file = 'empty_badge_for_{}.csv'.format(role)
        logger.info('Creating empty data csv file "{}".'.format(empty_badges_csv_file))
        empty_data = empty_data_for_blank_badge(role)
        empty_df = pd.DataFrame.from_dict(empty_data)
        empty_df.to_csv(empty_badges_csv_file, index=False)

        template_file = os.path.join(TEMPLATES_DIR, badge_template_file(role))
        create_badge_set(input_file=empty_badges_csv_file, template_file=template_file, outdir=outdir)
        os.remove(empty_badges_csv_file)


@task
def split_users_csv(ctx, users_file=USERS_FILE):
    df = pd.read_csv(users_file)

    col_maxlengths = {col.replace(' ', '_'):length for col, length in MAXLENGTHS.items()}
    df = wrap_cell_contents(df, field_maxlength=col_maxlengths)

    for role, template in ROLETAG_TEMPLATES.items():
        role_df = df[df.tags.str.contains(role, regex=False)]
        df = df.drop(role_df.index)
        output_file = add_suffix(users_file, role)
        role_df.to_csv(output_file, index=False)


@task
def create_badges_for(ctx, role, users_file=USERS_FILE, outdir='stamped'):
    input_file = add_suffix(users_file, role)
    template_file = os.path.join(TEMPLATES_DIR, badge_template_file(role))
    create_badge_set(input_file=input_file, outdir=outdir, template_file=template_file)


@task
def make_all_badges(ctx, users_file=USERS_FILE, outdir='stamped'):
    for role, template in ROLETAG_TEMPLATES.items():
        create_badges_for(ctx, role, users_file=users_file, outdir=outdir)


@task
def convert_badges_to_cmyk(ctx, stamped_dir='stamped', cleanup=True):
    pdf_files = glob(os.path.join(stamped_dir, '*.pdf'))
    for pdf_filepath in pdf_files:
        if pdf_filepath.endswith('joined.pdf'):
            continue
        pdf_to_cmyk(pdf_filepath, add_suffix(pdf_filepath, 'cmyk'))

        if cleanup:
            os.remove(pdf_filepath)


@task
def make_badge_faces(ctx, stamped_dir='stamped', cleanup=True):
    pdf_files = glob(os.path.join(stamped_dir, '*.pdf'))
    for pdf_filepath in pdf_files:
        if pdf_filepath.endswith('joined.pdf'):
            continue

        pdf_pair_file = create_badge_faces(pdf_filepath)
        logger.info('Created {}'.format(pdf_pair_file))
        if cleanup:
            os.remove(pdf_filepath)


@task
def merge_tickets(ctx, input_file, output_file, on=['email'], column_concat={'order': '+'}):
    df = pd.read_csv(input_file).fillna('')
    df = df.groupby(by=on).agg(column_concat).reset_index()
    df.to_csv(output_file, index=False)


@task
def add_tags(ctx, input_file, output_file):
    df = pd.read_csv(input_file)
    for ticket_type, new_tag in TICKET_TYPE_TEMPLATES.items():
        df.loc[(df.ticket_type == ticket_type) & (df.tags.isna()), 'tags'] = new_tag
    df.to_csv(output_file, index=False)


@task
def rename_columns(ctx, input_file, output_file):
    df = pd.read_csv(input_file).fillna('')
    df.rename(columns=COLUMNS_RENAME, inplace=True)
    df.to_csv(output_file, index=False)


@task
def filter_tickets(ctx, input_file, output_file):
    df = pd.read_csv(input_file, na_values='-').fillna('')
    for col, values in FILTER_TICKETS.items():
        logger.debug(f'Filtering {col} columns that do not contain any of {values}.')
        df = df.loc[df[col].isin(values)]
    df.to_csv(output_file, index=False)


@task
def escape_csv(ctx, input_file):
    with open(input_file, 'r') as csvfile:
        data = csvfile.read()
    escaped_data = re.sub(r'&(?!amp)', '&amp;', data)
    with open(input_file, 'w') as csvfile:
        csvfile.write(escaped_data)


@task
def make_blank_badges(ctx, outdir='blank'):
    create_empty_badges(ctx, outdir=outdir)
    convert_badges_to_cmyk(ctx, stamped_dir=outdir)
    make_badge_faces(ctx, stamped_dir=outdir, cleanup=True)


@task
def all(ctx, input_file=USERS_FILE, outdir='stamped'):
    # escape_csv(ctx, input_file=input_file)
    cleaned_file = add_suffix(input_file, 'cleaned')
    filter_tickets(ctx, input_file=input_file, output_file=cleaned_file)

    renamed_file = add_suffix(cleaned_file, 'renamed')
    rename_columns(ctx, input_file=cleaned_file, output_file=renamed_file)

    tagged_file = add_suffix(renamed_file, 'retagged')
    add_tags(ctx, input_file=renamed_file, output_file=tagged_file)

    if GROUP_ROWS_BY:
        merged_file = add_suffix(tagged_file, 'merged')
        merge_tickets(
            ctx,
            input_file=tagged_file,
            output_file=merged_file,
            on=GROUP_ROWS_BY,
            column_concat=GROUP_FUNC,
        )
        tickets_file = merged_file
    else:
        tickets_file = tagged_file

    split_users_csv(ctx, users_file=tickets_file)
    make_all_badges(ctx, users_file=tickets_file, outdir=outdir)
    convert_badges_to_cmyk(ctx, stamped_dir=outdir)
    make_badge_faces(ctx, stamped_dir=outdir, cleanup=True)

    make_blank_badges(ctx)

