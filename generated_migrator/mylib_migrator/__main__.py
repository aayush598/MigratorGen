"""
mylib_migrator - Auto-generated code migrator for mylib
Generated on: 2026-04-22 15:55:24
Versions covered: 1.1.0 - 3.0.0

Usage:
    python -m mylib_migrator list-versions
    python -m mylib_migrator migrate --from 1.0.0 --to 2.0.0 ./project/
    python -m mylib_migrator migrate --from 1.0.0 --to latest ./project/ --dry-run
"""

import sys, json, argparse, difflib, re
from pathlib import Path
from typing import List, Tuple, Optional

# Embedded migration rules (JSON string - avoids null/true/false Python syntax issues)
_MIGRATION_JSON = "{\"1.1.0\": [{\"change_type\": \"deprecate_function\", \"version_introduced\": \"1.1.0\", \"description\": \"fetch_data() is deprecated, use get_data() instead\", \"old_name\": \"fetch_data\", \"new_name\": null, \"function_name\": null, \"argument_name\": null, \"new_argument_name\": null, \"default_value\": null, \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": \"get_data\", \"removal_version\": null, \"decorator_name\": null, \"source_module\": null, \"target_module\": null, \"extra\": {}}], \"2.0.0\": [{\"change_type\": \"rename_function\", \"version_introduced\": \"2.0.0\", \"description\": \"Renamed connect() to create_connection()\", \"old_name\": \"connect\", \"new_name\": \"create_connection\", \"function_name\": null, \"argument_name\": null, \"new_argument_name\": null, \"default_value\": null, \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": null, \"removal_version\": null, \"decorator_name\": null, \"source_module\": null, \"target_module\": null, \"extra\": {}}, {\"change_type\": \"rename_class\", \"version_introduced\": \"2.0.0\", \"description\": \"Client class renamed to APIClient\", \"old_name\": \"Client\", \"new_name\": \"APIClient\", \"function_name\": null, \"argument_name\": null, \"new_argument_name\": null, \"default_value\": null, \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": null, \"removal_version\": null, \"decorator_name\": null, \"source_module\": null, \"target_module\": null, \"extra\": {}}, {\"change_type\": \"rename_import\", \"version_introduced\": \"2.0.0\", \"description\": \"Client moved to new module\", \"old_name\": \"Client\", \"new_name\": \"APIClient\", \"function_name\": null, \"argument_name\": null, \"new_argument_name\": null, \"default_value\": null, \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": \"mylib\", \"new_module\": \"mylib.client\", \"replacement\": null, \"removal_version\": null, \"decorator_name\": null, \"source_module\": null, \"target_module\": null, \"extra\": {}}, {\"change_type\": \"add_argument\", \"version_introduced\": \"2.0.0\", \"description\": \"Added timeout parameter to create_connection()\", \"old_name\": null, \"new_name\": null, \"function_name\": \"create_connection\", \"argument_name\": \"timeout\", \"new_argument_name\": null, \"default_value\": \"30\", \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": null, \"removal_version\": null, \"decorator_name\": null, \"source_module\": null, \"target_module\": null, \"extra\": {}}, {\"change_type\": \"rename_attribute\", \"version_introduced\": \"2.0.0\", \"description\": \"Renamed .url attribute to .base_url\", \"old_name\": \"url\", \"new_name\": \"base_url\", \"function_name\": null, \"argument_name\": null, \"new_argument_name\": null, \"default_value\": null, \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": null, \"removal_version\": null, \"decorator_name\": null, \"source_module\": null, \"target_module\": null, \"extra\": {}}], \"2.1.0\": [{\"change_type\": \"remove_argument\", \"version_introduced\": \"2.1.0\", \"description\": \"Removed deprecated verbose argument from send_request()\", \"old_name\": null, \"new_name\": null, \"function_name\": \"send_request\", \"argument_name\": \"verbose\", \"new_argument_name\": null, \"default_value\": null, \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": null, \"removal_version\": null, \"decorator_name\": null, \"source_module\": null, \"target_module\": null, \"extra\": {}}, {\"change_type\": \"move_to_module\", \"version_introduced\": \"2.1.0\", \"description\": \"Moved Formatter class to mylib.utils\", \"old_name\": \"Formatter\", \"new_name\": null, \"function_name\": null, \"argument_name\": null, \"new_argument_name\": null, \"default_value\": null, \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": null, \"removal_version\": null, \"decorator_name\": null, \"source_module\": \"mylib.helpers\", \"target_module\": \"mylib.utils\", \"extra\": {}}, {\"change_type\": \"replace_with_property\", \"version_introduced\": \"2.1.0\", \"description\": \"get_name() replaced by .name property\", \"old_name\": \"get_name\", \"new_name\": \"name\", \"function_name\": null, \"argument_name\": null, \"new_argument_name\": null, \"default_value\": null, \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": null, \"removal_version\": null, \"decorator_name\": null, \"source_module\": null, \"target_module\": null, \"extra\": {}}], \"3.0.0\": [{\"change_type\": \"rename_function\", \"version_introduced\": \"3.0.0\", \"description\": \"send_request() renamed to request()\", \"old_name\": \"send_request\", \"new_name\": \"request\", \"function_name\": null, \"argument_name\": null, \"new_argument_name\": null, \"default_value\": null, \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": null, \"removal_version\": null, \"decorator_name\": null, \"source_module\": null, \"target_module\": null, \"extra\": {}}, {\"change_type\": \"add_decorator\", \"version_introduced\": \"3.0.0\", \"description\": \"All handler functions must be decorated with @handler\", \"old_name\": null, \"new_name\": null, \"function_name\": \"on_response\", \"argument_name\": null, \"new_argument_name\": null, \"default_value\": null, \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": null, \"removal_version\": null, \"decorator_name\": \"handler\", \"source_module\": null, \"target_module\": null, \"extra\": {}}, {\"change_type\": \"change_argument_default\", \"version_introduced\": \"3.0.0\", \"description\": \"Default timeout changed from 30 to 60\", \"old_name\": null, \"new_name\": null, \"function_name\": \"create_connection\", \"argument_name\": \"timeout\", \"new_argument_name\": null, \"default_value\": \"60\", \"argument_position\": null, \"new_argument_value\": null, \"new_order\": null, \"old_module\": null, \"new_module\": null, \"replacement\": null, \"removal_version\": null, \"decorator_name\": null, \"source_module\": null, \"target_module\": null, \"extra\": {}}]}"
MIGRATION_DATA = json.loads(_MIGRATION_JSON)

try:
    import libcst as cst
    _CST = True
except ImportError:
    _CST = False
    print('[WARNING] libcst not found. Run: pip install libcst')


def _vk(v):
    return tuple(int(x) for x in re.findall(r'\d+', v))


def _dn(node):
    if node is None: return ''
    if isinstance(node, cst.Name): return node.value
    if isinstance(node, cst.Attribute): return _dn(node.value) + '.' + node.attr.value
    return ''


def _mn(name):
    parts = name.split('.')
    node = cst.Name(parts[0])
    for p in parts[1:]:
        node = cst.Attribute(value=node, attr=cst.Name(p))
    return node


def _cn(f):
    if isinstance(f, cst.Name): return f.value
    if isinstance(f, cst.Attribute): return f.attr.value
    return ''


class B(cst.CSTTransformer):
    def __init__(self, r): self.r = r; self.ch = []
    def rec(self, m): self.ch.append(m)


class RF(B):
    def leave_Name(self, o, u):
        if u.value == self.r.get('old_name'):
            self.rec('Renamed ' + self.r['old_name'] + ' -> ' + self.r['new_name'])
            return u.with_changes(value=self.r['new_name'])
        return u

RC = RF  # rename_class uses same logic


class RA(B):
    def leave_Attribute(self, o, u):
        if isinstance(u.attr, cst.Name) and u.attr.value == self.r.get('old_name'):
            self.rec('Renamed .' + self.r['old_name'] + ' -> .' + self.r['new_name'])
            return u.with_changes(attr=cst.Name(self.r['new_name']))
        return u


class RI(B):
    def leave_ImportFrom(self, o, u):
        mod = _dn(u.module) if u.module else ''
        om, nm = self.r.get('old_module',''), self.r.get('new_module','')
        on, nn = self.r.get('old_name',''), self.r.get('new_name','')
        if mod != om: return u
        nmn = _mn(nm) if nm else u.module
        if isinstance(u.names, cst.ImportStar): return u.with_changes(module=nmn)
        nl2, changed = [], False
        for a in u.names:
            if _dn(a.name) == on and nn:
                nl2.append(a.with_changes(name=cst.Name(nn)))
                changed = True
                self.rec('Renamed import ' + on + ' -> ' + nn + ' in ' + nm)
            else: nl2.append(a)
        if not changed: return u
        return u.with_changes(module=nmn, names=nl2)


class AA(B):
    def leave_Call(self, o, u):
        if _cn(u.func) != self.r.get('function_name'): return u
        for a in u.args:
            if a.keyword and a.keyword.value == self.r.get('argument_name'): return u
        dv = self.r.get('default_value') or 'None'
        na = cst.Arg(keyword=cst.Name(self.r['argument_name']),
            value=cst.parse_expression(dv),
            equal=cst.AssignEqual(whitespace_before=cst.SimpleWhitespace(''),
                whitespace_after=cst.SimpleWhitespace('')))
        args = list(u.args)
        if args: args[-1] = args[-1].with_changes(comma=cst.MaybeSentinel.DEFAULT)
        args.append(na)
        self.rec('Added ' + self.r['argument_name'] + '=' + dv + ' to ' + self.r['function_name'] + '()')
        return u.with_changes(args=args)


class RemA(B):
    def leave_Call(self, o, u):
        if _cn(u.func) != self.r.get('function_name'): return u
        na = [a for a in u.args if not (a.keyword and a.keyword.value == self.r.get('argument_name'))]
        if len(na) < len(u.args):
            if na: na[-1] = na[-1].with_changes(comma=cst.MaybeSentinel.DEFAULT)
            self.rec('Removed ' + self.r['argument_name'] + ' from ' + self.r['function_name'] + '()')
            return u.with_changes(args=na)
        return u


class MM(B):
    def leave_ImportFrom(self, o, u):
        mod = _dn(u.module) if u.module else ''
        if mod != self.r.get('source_module'): return u
        if isinstance(u.names, cst.ImportStar): return u
        for a in u.names:
            if _dn(a.name) == self.r.get('old_name'):
                self.rec('Moved ' + self.r['old_name'] + ' to ' + self.r['target_module'])
                return u.with_changes(module=_mn(self.r['target_module']))
        return u


class RWP(B):
    def leave_Call(self, o, u):
        if not isinstance(u.func, cst.Attribute): return u
        if u.func.attr.value != self.r.get('old_name'): return u
        if u.args: return u
        self.rec('Replaced ' + self.r['old_name'] + '() with .' + self.r['new_name'])
        return u.func.with_changes(attr=cst.Name(self.r['new_name']))


class AD(B):
    def leave_FunctionDef(self, o, u):
        if u.name.value != self.r.get('function_name'): return u
        dn = self.r.get('decorator_name')
        for d in u.decorators:
            if isinstance(d.decorator, cst.Name) and d.decorator.value == dn: return u
        nd = cst.Decorator(decorator=cst.Name(dn), leading_lines=[])
        self.rec('Added @' + dn + ' to ' + self.r['function_name'])
        return u.with_changes(decorators=[*u.decorators, nd])


class RD(B):
    def leave_FunctionDef(self, o, u):
        if u.name.value != self.r.get('function_name'): return u
        dn = self.r.get('decorator_name')
        nd = [d for d in u.decorators if not (isinstance(d.decorator, cst.Name) and d.decorator.value == dn)]
        if len(nd) < len(u.decorators):
            self.rec('Removed @' + dn + ' from ' + self.r['function_name'])
            return u.with_changes(decorators=nd)
        return u


class Dep(B):
    def leave_SimpleStatementLine(self, o, u):
        for s in u.body:
            if isinstance(s, cst.Expr) and isinstance(s.value, cst.Call):
                fn = _cn(s.value.func)
                if fn == self.r.get('old_name'):
                    repl = self.r.get('replacement','N/A')
                    c = cst.EmptyLine(comment=cst.Comment('# DEPRECATED: ' + fn + '() use ' + repl))
                    self.rec('Marked ' + fn + '() as deprecated')
                    return u.with_changes(leading_lines=[*u.leading_lines, c])
        return u


class CAD(B):
    def leave_Param(self, o, u):
        if u.name.value != self.r.get('argument_name'): return u
        nd = self.r.get('default_value')
        if nd is None: return u
        self.rec('Changed default of ' + self.r['argument_name'] + ' to ' + nd)
        return u.with_changes(default=cst.parse_expression(nd))


_TM = {
    'rename_function': RF, 'rename_class': RC,
    'rename_attribute': RA, 'rename_import': RI,
    'add_argument': AA, 'remove_argument': RemA,
    'move_to_module': MM, 'replace_with_property': RWP,
    'add_decorator': AD, 'remove_decorator': RD,
    'deprecate_function': Dep, 'remove_function': Dep,
    'change_argument_default': CAD,
}


def _apply(code, rule):
    if not _CST: return code, []
    cls = _TM.get(rule.get('change_type'))
    if cls is None: return code, []
    t = cls(rule)
    try:
        return cst.parse_module(code).visit(t).code, t.ch
    except Exception as e:
        return code, ['[ERR] ' + str(e)]


def _versions():
    return sorted(MIGRATION_DATA.keys(), key=_vk)


def _resolve(src, tgt):
    vs = _versions()
    if tgt == 'latest': tgt = vs[-1]
    sk, tk = _vk(src), _vk(tgt)
    up = tk > sk
    rules = []
    if up:
        for v in vs:
            if _vk(v) > sk and _vk(v) <= tk: rules.extend(MIGRATION_DATA[v])
    else:
        for v in reversed(vs):
            if _vk(v) > tk and _vk(v) <= sk: rules.extend(MIGRATION_DATA[v])
    return rules, tgt, up


def migrate_code(source_code, rules):
    '''Migrate source code string. Returns (new_code, changes).'''
    code, all_ch = source_code, []
    for r in rules:
        nc, ch = _apply(code, r)
        if nc != code: code = nc; all_ch.extend(ch)
    return code, all_ch


def migrate_file(path, rules, dry_run=False, backup=True):
    '''Migrate a file in place. Returns (was_modified, changes).'''
    path = Path(path)
    src = path.read_text(encoding='utf-8')
    nc, ch = migrate_code(src, rules)
    mod = nc != src
    if mod and not dry_run:
        if backup: path.with_suffix('.py.bak').write_text(src, encoding='utf-8')
        path.write_text(nc, encoding='utf-8')
    return mod, ch


def preview_diff(source_code, rules):
    '''Return unified diff string.'''
    nc, ch = migrate_code(source_code, rules)
    if nc == source_code: return 'No changes would be made.'
    d = difflib.unified_diff(source_code.splitlines(keepends=True),
        nc.splitlines(keepends=True), fromfile='original', tofile='migrated')
    hdr = 'Changes:\n' + '\n'.join('  - ' + c for c in ch) + '\n\n'
    return hdr + ''.join(d)


def main():
    p = argparse.ArgumentParser(description='mylib_migrator migrator')
    s = p.add_subparsers(dest='cmd')

    lv = s.add_parser('list-versions')

    m = s.add_parser('migrate')
    m.add_argument('path')
    m.add_argument('--from', dest='fv', required=True)
    m.add_argument('--to', dest='tv', default='latest')
    m.add_argument('--dry-run', action='store_true')
    m.add_argument('--no-backup', action='store_true')
    m.add_argument('--preview', action='store_true')

    val = s.add_parser('validate')
    val.add_argument('file')

    args = p.parse_args()

    if args.cmd == 'list-versions':
        print('\nAvailable versions for mylib:')
        for v in _versions():
            n = len(MIGRATION_DATA[v])
            print('  v' + v + '  (' + str(n) + ' rule' + ('s' if n!=1 else '') + ')')
        print()
        return

    if args.cmd == 'validate':
        code = Path(args.file).read_text(encoding='utf-8')
        try: cst.parse_module(code); print('OK:', args.file)
        except Exception as e: print('FAIL:', e); sys.exit(1)
        return

    if args.cmd == 'migrate':
        rules, tgt, up = _resolve(args.fv, args.tv)
        d = 'Upgrading' if up else 'Downgrading'
        print('\n' + d + ': v' + args.fv + ' to v' + tgt)
        print('Applying ' + str(len(rules)) + ' rule(s)...')
        sp = Path(args.path)
        files = list(sp.rglob('*.py')) if sp.is_dir() else [sp]
        mc = 0
        for f in files:
            if args.preview:
                src = f.read_text(encoding='utf-8')
                diff = preview_diff(src, rules)
                if diff != 'No changes would be made.':
                    print('\n=== ' + str(f) + ' ===')
                    print(diff)
            else:
                mod, ch = migrate_file(f, rules, dry_run=args.dry_run, backup=not args.no_backup)
                if mod or ch:
                    print('\n  ' + str(f) + ':')
                    for c in ch: print('    + ' + c)
                    mc += 1
        tag = '[DRY RUN] ' if args.dry_run else ''
        verb = 'would be modified' if args.dry_run else 'modified'
        print('\n' + tag + 'Done: ' + str(mc) + '/' + str(len(files)) + ' file(s) ' + verb + '.')
        return

    p.print_help()


if __name__ == '__main__':
    main()
