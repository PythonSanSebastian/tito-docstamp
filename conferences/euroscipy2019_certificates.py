import logging
import os
import shutil
import subprocess
import sys
import urllib
from glob import glob
from typing import Any, List
from uuid import uuid4

import pandas as pd
from invoke import task

from docstamp.inkscape import svg2pdf

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(log_format)
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


def join_strings(items: List[Any], symbol: str = ''):
    return symbol.join(sorted({item for item in items if item}))


TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'templates',
    'euroscipy2019'
)

CONFERENCE_NAME = 'euroscipy'

USERS_FILE = 'tito.csv'

COLUMNS_RENAME = {
    'Order Reference': 'order',
    'Number': 'number',
    'Ticket': 'ticket',
    'Ticket Full Name': 'full_name',
    'Ticket Email': 'email',
    'Ticket Company Name': 'company',
}

FILTER_TICKETS = {
    'Ticket': {
        'Financial Aid Ticket',
        # 'Bronze sponsorship',
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
    },
}

TEMPLATE = 'certificate_of_attendance.svg'

GROUP_ROWS_BY = ['email']

GROUP_FUNC = {
    'ticket': '|'.join,
    'full_name': first_true,
}

STORAGE_URL = 'https://storage.cloud.google.com/euroscipy-certificates/2019'

def add_suffix(input_file: str, suffix: str) -> str:
    extension = input_file.split('.')[-1]
    return input_file.replace(f'.{extension}', f'_{suffix}.{extension}')


def badge_template_file() -> str:
    return TEMPLATE


def get_file_url(base_url, file_path) -> str:
    url = f'{base_url}/{file_path}'
    return urllib.parse.quote(url)


def render_files(input_file, output_dir, template_file, output_type='svg'):
    cmd = 'docstamp create --unicode_support '
    cmd += f'-i "{input_file}" '
    cmd += f'-t "{template_file}" '
    cmd += f'-f "email" '
    cmd += f'--dpi 150 '
    cmd += f'-o "{output_dir}" '
    cmd += f'-d {output_type}'
    logger.info('Calling {}'.format(cmd))
    subprocess.call(cmd, shell='True')


# def _center_object(object_id, filepath):
#     cmd = 'inkscape '
#     cmd += f'--verb=EditSelect '
#     cmd += f'--select={object_id} '
#     cmd += f'--verb=AlignHorizontalCenter '
#     cmd += f'--verb=FileSave '
#     cmd += f'--verb=FileQuit '
#     cmd += filepath
#     logger.info('Calling {}'.format(cmd))
#     subprocess.call(cmd, shell='True')


# @task
# def center_names(ctx, output_dir):
#     for filepath in glob(os.path.join(output_dir, '*.svg')):
#         _center_object('full_name', filepath)


@task
def svg_to_pdf(ctx, output_dir):
    for filepath in glob(os.path.join(output_dir, '**', '*.svg')):
        svg2pdf(filepath, filepath.replace('.svg', '.pdf'))


@task
def delete_svg_files(ctx, input_dir):
    for filepath in glob(os.path.join(input_dir, '**', '*.svg')):
        os.remove(filepath)


@task
def merge_tickets(ctx, input_file, output_file, on=['email'], column_concat={'order': '+'}):
    df = pd.read_csv(input_file).fillna('')
    df = df.groupby(by=on).agg(column_concat).reset_index()
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
def add_conference_and_tutorials_column(ctx, input_file, output_file):
    def column_value(entry):
        tickets = entry.ticket
        if 'Conference' in tickets and 'Tutorials' in tickets:
            return 'conference and tutorials'
        if 'Conference' in tickets:
            return 'conference'
        if 'Tutorials' in tickets:
            return 'tutorials'
        if 'Invited speaker' in tickets:
            return 'conference'
        if 'Financial Aid Ticket' in tickets:
            return 'conference and tutorials'
        if 'Bronze sponsorship' in tickets:
            return 'conference and tutorials'

    df = pd.read_csv(input_file).fillna('')
    df['conference_and_tutorials'] = df.apply(column_value, axis=1)
    df.to_csv(output_file, index=False)


@task
def add_uuid(ctx, input_file, output_file):
    df = pd.read_csv(input_file).fillna('')
    df['uuid'] = [uuid4() for i in range(len(df))]
    df.to_csv(output_file, index=False)


@task
def add_url(ctx, input_file, output_file):
    def get_certificate_url(entry):
        file_path = urllib.parse.quote(f'{entry.uuid}/certificate_of_attendance_{entry.email}.pdf')
        return f'{STORAGE_URL}/{file_path}'

    df = pd.read_csv(input_file).fillna('')
    df['url'] = df.apply(get_certificate_url, axis=1)
    df.to_csv(output_file, index=False)


@task
def move_to_uuid_folders(ctx, input_file, input_dir, output_dir):
    def move_to_uuid_folder(entry):
        file = list(glob(os.path.join(input_dir, f'*{entry.email}.svg')))[0]
        uuid = entry.uuid
        new_dir = os.path.join(output_dir, uuid)
        os.makedirs(new_dir)
        shutil.move(file, new_dir)

    df = pd.read_csv(input_file).fillna('')
    df.apply(move_to_uuid_folder, axis=1)
    # for entry in df.itertuples():
    #     move_to_uuid_folder(entry)


@task
def certificates(ctx, input_file=USERS_FILE, output_dir='certificates'):
    cleaned_file = add_suffix(input_file, 'cleaned')
    filter_tickets(ctx, input_file=input_file, output_file=cleaned_file)

    renamed_file = add_suffix(cleaned_file, 'renamed')
    rename_columns(ctx, input_file=cleaned_file, output_file=renamed_file)

    merged_file = add_suffix(renamed_file, 'merged')
    merge_tickets(
        ctx,
        input_file=renamed_file,
        output_file=merged_file,
        on=GROUP_ROWS_BY,
        column_concat=GROUP_FUNC,
    )

    tagged_file = add_suffix(merged_file, 'tagged')
    add_conference_and_tutorials_column(ctx, input_file=merged_file, output_file=tagged_file)
    add_uuid(ctx, input_file=tagged_file, output_file=tagged_file)
    add_url(ctx, input_file=tagged_file, output_file=tagged_file)

    tickets_file = tagged_file
    template_file = os.path.join(TEMPLATES_DIR, badge_template_file())
    render_files(tickets_file, output_dir=output_dir, template_file=template_file, output_type='svg')
    move_to_uuid_folders(ctx, tickets_file, input_dir=output_dir, output_dir=output_dir)
    # center_names(ctx, output_dir=output_dir)
    svg_to_pdf(ctx, output_dir=output_dir)
    delete_svg_files(ctx, input_dir=output_dir)
