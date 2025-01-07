# emycin.py
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def write(line): 
    print(line)

def cf_or(a, b):
    """The OR of two certainty factors."""
    if a > 0 and b > 0:
        return a + b - a * b
    elif a < 0 and b < 0:
        return a + b + a * b
    else:
        return (a + b) / (1 - min(abs(a), abs(b)))

def cf_and(a, b):
    """The AND of two certainty factors."""
    return min(a, b)

def is_cf(x):
    """Is x a valid certainty factor; ie, is (false <= x <= true)?"""
    return CF.false <= x <= CF.true

def cf_true(x):
    """Do we consider x true?"""
    return is_cf(x) and x > CF.cutoff

def cf_false(x):
    """Do we consider x false?"""
    return is_cf(x) and x < (CF.cutoff - 1)

class CF:
    """Collect important certainty factors in a single namespace."""
    true = 1.0
    false = -1.0
    unknown = 0.0
    cutoff = 0.2

class Context:
    def __init__(self, name, initial_data=None, goals=None):
        self.count = 0
        self.name = name
        self.initial_data = initial_data or []
        self.goals = goals or []
    
    def instantiate(self):
        inst = (self.name, self.count)
        self.count += 1
        return inst

class Parameter:
    def __init__(self, name, ctx=None, enum=None, cls=None, ask_first=False):
        self.name = name
        self.ctx = ctx
        self.enum = enum
        self.ask_first = ask_first
        self.cls = cls
        
    def type_string(self):
        return self.cls.__name__ if self.cls else '(%s)' % ', '.join(list(self.enum))
    
    def from_string(self, val):
        if self.cls:
            return self.cls(val)
        if self.enum and val in self.enum:
            return val
        raise ValueError(f'val must be one of {", ".join(list(self.enum))} for the parameter {self.name}')

def eval_condition(condition, values, find_out=None):
    logging.debug('Evaluating condition [%s] (find_out %s)',
                  print_condition(condition), 'ENABLED' if find_out else 'DISABLED')
    
    param, inst, op, val = condition
    if find_out:
        find_out(param, inst)
    total = sum(cf for known_val, cf in list(values.items()) if op(known_val, val))
    
    logging.debug('Condition [%s] has a certainty factor of %f',
                  print_condition(condition), total)
    
    return total

def print_condition(condition):
    param, inst, op, val = condition
    name = inst if isinstance(inst, str) else inst[0]
    opname = op.__name__
    return '%s %s %s %s' % (param, name, opname, val)

def get_vals(values, param, inst):
    return values.setdefault((param, inst), {})

def get_cf(values, param, inst, val):
    vals = get_vals(values, param, inst)
    return vals.setdefault(val, CF.unknown)

def update_cf(values, param, inst, val, cf):
    existing = get_cf(values, param, inst, val)
    updated = cf_or(existing, cf)
    get_vals(values, param, inst)[val] = updated

class Rule:
    def __init__(self, num, premises, conclusions, cf):
        self.num = num
        self.cf = cf
        self.raw_premises = premises
        self.raw_conclusions = conclusions
    
    def __str__(self):
        prems = list(map(print_condition, self.raw_premises))
        concls = list(map(print_condition, self.raw_conclusions))
        templ = 'RULE %d\nIF\n\t%s\nTHEN %f\n\t%s'
        return templ % (self.num, '\n\t'.join(prems), self.cf, '\n\t'.join(concls))
    
    def clone(self):
        return Rule(self.num, list(self.raw_premises),
                    list(self.raw_conclusions), self.cf)
    
    def _bind_cond(self, cond, instances):
        param, ctx, op, val = cond
        return param, instances[ctx], op, val
        
    def premises(self, instances):
        return [self._bind_cond(premise, instances) for premise in self.raw_premises]
    
    def conclusions(self, instances):
        return [self._bind_cond(concl, instances) for concl in self.raw_conclusions]
    
    def applicable(self, values, instances, find_out=None):
        for premise in self.premises(instances):
            param, inst, op, val = premise
            vals = get_vals(values, param, inst)
            cf = eval_condition(premise, vals)
            if cf_false(cf):
                return CF.false
                        
        logging.debug('Determining applicability of rule (\n%s\n)', self)
        
        total_cf = CF.true
        for premise in self.premises(instances):
            param, inst, op, val = premise
            vals = get_vals(values, param, inst)
            cf = eval_condition(premise, vals, find_out)
            total_cf = cf_and(total_cf, cf)
            if not cf_true(total_cf):
                return CF.false
        return total_cf
    
    def apply(self, values, instances, find_out=None, track=None):
        if track:
            track(self)
        
        logging.debug('Attempting to apply rule (\n%s\n)', self)

        cf = self.cf * self.applicable(values, instances, find_out)
        if not cf_true(cf):
            logging.debug('Rule (\n%s\n) is not applicable (%f certainty)', self, cf)
            return False
        
        logging.info('Applying rule (\n%s\n) with certainty %f', self, cf)
        
        for conclusion in self.conclusions(instances):
            param, inst, op, val = conclusion
            logging.info('Concluding [%s] with certainty %f',
                         print_condition(conclusion), cf)
            update_cf(values, param, inst, val, cf)
        
        return True

def use_rules(values, instances, rules, find_out=None, track_rules=None):
    return any([rule.apply(values, instances, find_out, track_rules) for rule in rules])

class Shell:
    HELP = """Type one of the following:
?       - to see possible answers for this parameter
rule    - to show the current rule
why     - to see why this question is asked
help    - to show this message
unknown - if the answer to this question is not known
<val>   - a single definite answer to the question
<val1> <cf1> [, <val2> <cf2>, ...]
        - if there are multiple answers with associated certainty factors."""

    def __init__(self, read=input, write=write):
        self.read = read
        self.write = write
        self.rules = {}
        self.contexts = {}
        self.params = {}
        self.known = set()
        self.asked = set()
        self.known_values = {}
        self.current_inst = None
        self.instances = {}
        self.current_rule = None
    
    def clear(self):
        self.known.clear()
        self.asked.clear()
        self.known_values.clear()
        self.current_inst = None
        self.current_rule = None
        self.instances.clear()
    
    def define_rule(self, rule):
        for param, ctx, op, val in rule.raw_conclusions:
            self.rules.setdefault(param, []).append(rule)
    
    def define_context(self, ctx):
        self.contexts[ctx.name] = ctx
        
    def define_param(self, param):
        self.params[param.name] = param
    
    def get_rules(self, param):
        return self.rules.setdefault(param, [])
    
    def instantiate(self, ctx_name):
        inst = self.contexts[ctx_name].instantiate()
        self.current_inst = inst
        self.instances[ctx_name] = inst
        return inst
    
    def get_param(self, name):
        return self.params.setdefault(name, Parameter(name))

    def ask_values(self, param, inst):
        if (param, inst) in self.asked:
            return
        logging.debug('Getting user input for %s of %s', param, inst)
        
        self.asked.add((param, inst))
        while True:
            resp = self.read('What is the %s of %s-%d? ' % (param, inst[0], inst[1]))
            if not resp:
                continue
            if resp == 'unknown':
                return False
            elif resp == 'help':
                self.write(Shell.HELP)
            elif resp == 'why':
                self.print_why(param)
            elif resp == 'rule':
                self.write(self.current_rule)
            elif resp == '?':
                self.write('%s must be of type %s' %
                           (param, self.get_param(param).type_string()))
            else:
                try:
                    for val, cf in parse_reply(self.get_param(param), resp):
                        update_cf(self.known_values, param, inst, val, cf)
                    return True
                except:
                    self.write('Invalid response. Type ? to see legal ones.')
    
    def print_why(self, param):
        self.write('Why is the value of %s being asked for?' % param)
        if self.current_rule in ('initial', 'goal'):
            self.write('%s is one of the %s parameters.' % (param, self.current_rule))
            return

        known, unknown = [], []
        for premise in self.current_rule.premises(self.instances):
            vals = get_vals(self.known_values, premise[0], premise[1])
            if cf_true(eval_condition(premise, vals)):
                known.append(premise)
            else:
                unknown.append(premise)
        
        if known:
            self.write('It is known that:')
            for condition in known:
                self.write(print_condition(condition))
            self.write('Therefore,')
        
        rule = self.current_rule.clone()
        rule.raw_premises = unknown
        self.write(rule)
    
    def _set_current_rule(self, rule):
        self.current_rule = rule
    
    def find_out(self, param, inst=None):
        inst = inst or self.current_inst

        if (param, inst) in self.known:
            return True
        
        def rules():
            return use_rules(self.known_values, self.instances,
                             self.get_rules(param), self.find_out,
                             self._set_current_rule)

        logging.debug('Finding out %s of %s', param, inst)

        if self.get_param(param).ask_first:
            success = self.ask_values(param, inst) or rules()
        else:
            success = rules() or self.ask_values(param, inst)
        if success:
            self.known.add((param, inst))
        return success
    
    def execute(self, context_names):
        logging.info('Beginning data-gathering for %s', ', '.join(context_names))
        
        self.write('Beginning execution. For help answering questions, type "help".')
        self.clear()
        results = {}
        for name in context_names:
            ctx = self.contexts[name]
            self.instantiate(name)
            
            self._set_current_rule('initial')
            for param in ctx.initial_data:
                self.find_out(param)
            
            self._set_current_rule('goal')
            for param in ctx.goals:
                self.find_out(param)
            
            if ctx.goals:
                result = {}
                for param in ctx.goals:
                    result[param] = get_vals(self.known_values, param, self.current_inst)
                results[self.current_inst] = result
            
        return results

def parse_reply(param, reply):
    if reply.find(',') >= 0:
        vals = []
        for pair in reply.split(','):
            val, cf = pair.strip().split(' ')
            vals.append((param.from_string(val), float(cf)))
        return vals
    return [(param.from_string(reply), CF.true)]

# mycin.py 
def eq(x, y):
    return x == y

def boolean(string):
    if string == 'True':
        return True
    if string == 'False':
        return False
    raise ValueError('bool must be True or False')

def define_contexts(sh):
    sh.define_context(Context('patient', ['name', 'sex', 'age']))
    sh.define_context(Context('culture', ['site', 'days-old']))
    sh.define_context(Context('organism', goals=['identity']))

def define_params(sh):
    sh.define_param(Parameter('name', 'patient', cls=str, ask_first=True))
    sh.define_param(Parameter('sex', 'patient', enum=['M', 'F'], ask_first=True))
    sh.define_param(Parameter('age', 'patient', cls=int, ask_first=True))
    sh.define_param(Parameter('burn', 'patient',
                              enum=['no', 'mild', 'serious'], ask_first=True))
    sh.define_param(Parameter('compromised-host', 'patient', cls=boolean))
    
    sh.define_param(Parameter('site', 'culture', enum=['blood'], ask_first=True))
    sh.define_param(Parameter('days-old', 'culture', cls=int, ask_first=True))
    
    organisms = ['pseudomonas', 'klebsiella', 'enterobacteriaceae',
                 'staphylococcus', 'bacteroides', 'streptococcus']
    sh.define_param(Parameter('identity', 'organism', enum=organisms, ask_first=True))
    sh.define_param(Parameter('gram', 'organism',
                              enum=['acid-fast', 'pos', 'neg'], ask_first=True))
    sh.define_param(Parameter('morphology', 'organism', enum=['rod', 'coccus']))
    sh.define_param(Parameter('aerobicity', 'organism', enum=['aerobic', 'anaerobic']))
    sh.define_param(Parameter('growth-conformation', 'organism',
                              enum=['chains', 'pairs', 'clumps']))

def define_rules(sh):
    sh.define_rule(Rule(52,
                        [('site', 'culture', eq, 'blood'),('gram', 'organism', eq, 'neg'),
                         ('morphology', 'organism', eq, 'rod'),
                         ('burn', 'patient', eq, 'serious')],
                        [('identity', 'organism', eq, 'pseudomonas')],
                        0.4))
    sh.define_rule(Rule(71,
                        [('gram', 'organism', eq, 'pos'),
                         ('morphology', 'organism', eq, 'coccus'),
                         ('growth-conformation', 'organism', eq, 'clumps')],
                        [('identity', 'organism', eq, 'staphylococcus')],
                        0.7))
    sh.define_rule(Rule(73,
                        [('site', 'culture', eq, 'blood'),
                         ('gram', 'organism', eq, 'neg'),
                         ('morphology', 'organism', eq, 'rod'),
                         ('aerobicity', 'organism', eq, 'anaerobic')],
                        [('identity', 'organism', eq, 'bacteroides')],
                        0.9))
    sh.define_rule(Rule(75,
                        [('gram', 'organism', eq, 'neg'),
                         ('morphology', 'organism', eq, 'rod'),
                         ('compromised-host', 'patient', eq, True)],
                        [('identity', 'organism', eq, 'pseudomonas')],
                        0.6))
    sh.define_rule(Rule(107,
                        [('gram', 'organism', eq, 'neg'),
                         ('morphology', 'organism', eq, 'rod'),
                         ('aerobicity', 'organism', eq, 'aerobic')],
                        [('identity', 'organism', eq, 'enterobacteriaceae')],
                        0.8))
    sh.define_rule(Rule(165,
                        [('gram', 'organism', eq, 'pos'),
                         ('morphology', 'organism', eq, 'coccus'),
                         ('growth-conformation', 'organism', eq, 'chains')],
                        [('identity', 'organism', eq, 'streptococcus')],
                        0.7))

def report_findings(findings):
    for inst, result in list(findings.items()):
        print('Findings for %s-%d:' % (inst[0], inst[1]))
        for param, vals in list(result.items()):
            possibilities = ['%s: %f' % (val[0], val[1]) for val in list(vals.items())]
            print('%s: %s' % (param, ', '.join(possibilities)))

def main():
    sh = Shell()
    define_contexts(sh)
    define_params(sh)
    define_rules(sh)
    report_findings(sh.execute(['patient', 'culture', 'organism']))

if __name__ == '__main__':
    main()