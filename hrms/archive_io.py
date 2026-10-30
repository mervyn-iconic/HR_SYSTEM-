"""Transactional import of the ZIP produced by the HR all-section export."""
import csv
import json
import io
import zipfile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError

ORDER = ['department','job','employee','attendance','job_history','salary','payroll','leave_type','leave_request','job_posting','job_application','performance_review','training','employee_training','benefit','employment_benefit']

def import_archive(engine,tables,validate,raw,preview=True):
    if len(raw)>10*1024*1024:
        raise ValueError('ZIP must be at most 10 MB.')
    try:
        archive=zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise ValueError('Choose a valid ZIP from Export all sections.')
    parsed={}
    with archive:
        infos=archive.infolist();names=[i.filename for i in infos]
        expected={n+'.csv' for n in ORDER}
        if len(names)!=len(set(names)):
            raise ValueError('ZIP contains duplicate file names.')
        if set(names)-expected-{'README.txt','manifest.json'} or not expected.issubset(names):
            raise ValueError('ZIP must contain all 16 section CSV files at its top level, as exported from Overview.')
        if sum(i.file_size for i in infos)>20*1024*1024 or any(i.file_size>5*1024*1024 for i in infos):
            raise ValueError('ZIP contents are too large (5 MB per file, 20 MB total).')
        escaped={}
        if 'manifest.json' in names:
            try:
                manifest=json.loads(archive.read('manifest.json'))
                if manifest.get('version')!=1 or not isinstance(manifest.get('escaped_cells'),dict): raise ValueError('Invalid export metadata.')
                escaped=manifest['escaped_cells']
            except (ValueError,TypeError,AttributeError) as exc:
                raise ValueError('Invalid export metadata.') from exc
        total=0
        for name in ORDER:
            try:
                text=archive.read(name+'.csv').decode('utf-8-sig')
                reader=csv.DictReader(io.StringIO(text),strict=True)
                fields=reader.fieldnames
                if not fields or len(fields)!=len(set(fields)) or set(fields)!={c.name for c in tables[name].c}:
                    raise ValueError('Headers must match the exported CSV, including its ID column.')
                pk=list(tables[name].primary_key)[0].name
                rows=[];ids=set()
                for row in reader:
                    line=reader.line_num
                    if None in row or any(v is None for v in row.values()):
                        raise ValueError(f'Row {line} has the wrong number of columns.')
                    record_id=int(row.pop(pk))
                    if record_id<1 or record_id in ids:
                        raise ValueError(f'Row {line} has a duplicate or invalid ID.')
                    marked=escaped.get(name,{})
                    if not isinstance(marked,dict): raise ValueError('Invalid export metadata.')
                    keys=marked.get(str(record_id),[])
                    if not isinstance(keys,list) or any(not isinstance(key,str) or key not in row for key in keys): raise ValueError('Invalid export metadata.')
                    for key in keys:
                        if row[key].startswith("'") and row[key][1:].startswith(('=','+','-','@','\t','\r')): row[key]=row[key][1:]
                    ids.add(record_id);rows.append((line,record_id,row));total+=1
                    if len(rows)>5000 or total>20000:
                        raise ValueError('Limit: 5,000 records per section and 20,000 across the ZIP.')
                parsed[name]=rows
            except (UnicodeError,csv.Error,ValueError,zipfile.BadZipFile,RuntimeError) as exc:
                raise ValueError(name+'.csv: '+str(exc)) from exc
    if not total:
        raise ValueError('The archive contains no records.')
    counts={};deferred=[]
    with engine.connect() as conn:
        transaction=conn.begin()
        try:
            for name in ORDER:
                table=tables[name];pk=list(table.primary_key)[0];created=updated=0
                for line,record_id,row in parsed[name]:
                    try:
                        exists=conn.execute(select(pk).where(pk==record_id)).first() is not None
                        values=validate(name,table,row,conn,record_id if exists else None)
                        if name=='department':
                            deferred.append((record_id,values.pop('manager_id',None)))
                            values['manager_id']=None
                        if exists:
                            conn.execute(table.update().where(pk==record_id).values(**values));updated+=1
                        else:
                            conn.execute(table.insert().values(**{pk.name:record_id,**values}));created+=1
                    except (IntegrityError,StatementError,ValueError,TypeError,ArithmeticError) as exc:
                        reason='Required, unique, range or linked-record validation failed.' if isinstance(exc,IntegrityError) else str(exc).split('\n')[0]
                        raise ValueError(f'{name}.csv row {line}: {reason}') from exc
                counts[name]={'created':created,'updated':updated}
            for record_id,manager_id in deferred:
                try:
                    conn.execute(tables['department'].update().where(tables['department'].c.department_id==record_id).values(manager_id=manager_id))
                except IntegrityError as exc:
                    raise ValueError(f'department.csv ID {record_id}: manager ID does not match an employee.') from exc
            if preview: transaction.rollback()
            else: transaction.commit()
        except Exception:
            transaction.rollback();raise
    return {'preview':preview,'sections':counts,'created':sum(c['created'] for c in counts.values()),'updated':sum(c['updated'] for c in counts.values()),'total':total}
