"""v7 rollout groups, matched on the feed product_type. Owner's order: sofas, tables (dining), bedrooms, rest.
Enabled groups are listed one per line in v7_groups.txt (empty file = v7 off everywhere)."""
import os
ORDER = ['sofas', 'tables', 'bedrooms', 'rest']
def group_of(pt):
    if 'Καναπέδες' in pt: return 'sofas'
    if 'Τραπέζια' in pt.split('>')[-1] or 'Τραπεζαρ' in pt: return 'tables'
    if any(k in pt for k in ('Κρεβάτ', 'Κρεβατοκάμαρ', 'Στρώματα', 'Κομοδίνα', 'Ντουλάπ', 'Toppers')): return 'bedrooms'
    return 'rest'
def enabled(path='v7_groups.txt'):
    return {l.strip() for l in open(path) if l.strip() and not l.startswith('#')} if os.path.exists(path) else set()
