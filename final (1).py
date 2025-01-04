import re
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
import csv

def readCsv(file_path):
    truth_table = []
    with open(file_path, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            truth_table.append({key: int(value) for key, value in row.items()})
    return truth_table

def toBoolean(truth_table):
    rows_with_output_1 = [row for row in truth_table if row["Q"] == 1]
    if not rows_with_output_1:
        return "0"  # If no output is 1, the expression is always 0.

    terms = []
    for row in rows_with_output_1:
        term = []
        for var, value in row.items():
            if var == "Q":  # Skip the output column
                continue
            if value == 1:
                term.append(var)  # Use variable directly
            else:
                term.append(f"~{var}")  # Negate the variable
        terms.append(" & ".join(term))  # AND terms together
    return "(" + ") ^ (".join(terms) + ")" # OR all terms together

file_path = "truth_table.csv"

truth_table = readCsv(file_path)
boolean_expression = toBoolean(truth_table)
print("Boolean Expression:", boolean_expression)

class QuantumBooleanCircuit:
    def __init__(self, expression: str):
        self.expression = expression
        self.variables = sorted(set(re.findall(r'~?[A-Z]', expression)))
        self.num_vars = len(self.variables)
        
        # Create quantum and classical registers
        self.qr = QuantumRegister(self.num_vars + 1)  # +1 for output qubit
        self.cr = ClassicalRegister(1)
        self.qc = QuantumCircuit(self.qr, self.cr)
        
        # Print qubit mapping
        self.print_qubit_mapping()
    
    def print_qubit_mapping(self):
        print("\n--- Qubit to Variable Mapping ---")
        for i, var in enumerate(self.variables):
            print(f"Qubit {i}: Variable {var}")
        print(f"Qubit {self.num_vars}: Output Qubit\n")
    
    def _get_variable_index(self, var: str) -> int:
        """Get the index of a variable, handling negation."""
        clean_var = var.replace('~', '')
        return self.variables.index(clean_var)
    
    def _multi_controlled_x(self, control_qubits, target_qubit):
        """Custom multi-controlled X gate implementation"""
        # Recursive implementation of multi-controlled X gate
        n = len(control_qubits)
        if n == 1:
            self.qc.cx(control_qubits[0], target_qubit)
        elif n == 2:
            self.qc.ccx(control_qubits[0], control_qubits[1], target_qubit)
        else:
            # Use ancilla qubit for more than 2 controls
            ancilla = QuantumRegister(1)
            self.qc.add_register(ancilla)
            
            # First create a multi-controlled ancilla state
            self.qc.h(ancilla[0])
            for ctrl in control_qubits[:-1]:
                self.qc.cx(ctrl, ancilla[0])
            
            # Then use the last control and ancilla to control X
            self.qc.ccx(control_qubits[-1], ancilla[0], target_qubit)
            
            # Uncompute the ancilla
            for ctrl in reversed(control_qubits[:-1]):
                self.qc.cx(ctrl, ancilla[0])
            self.qc.h(ancilla[0])
    
    def create_circuit(self) -> QuantumCircuit:
        """Create quantum circuit from Boolean expression."""
        # Parse clauses
        clauses = re.findall(r'\(([^)]+)\)', self.expression)
        
        for clause in clauses:
            # Prepare control qubits for this clause
            control_qubits = []
            
            # Process each term in the clause
            terms = clause.split('&')
            for term in terms:
                term = term.strip()
                var_idx = self._get_variable_index(term)
                
                if term.startswith('~'):
                    # Negated variable: apply X gate first
                    self.qc.x(self.qr[var_idx])
                
                control_qubits.append(self.qr[var_idx])
            
            # Apply multi-controlled X gate
            if control_qubits:
                self._multi_controlled_x(control_qubits, self.qr[self.num_vars])
            
            # Undo X gates for negated variables
            for term in terms:
                term = term.strip()
                if term.startswith('~'):
                    var_idx = self._get_variable_index(term)
                    self.qc.x(self.qr[var_idx])
        
        # Measure the output qubit
        self.qc.measure(self.qr[self.num_vars], self.cr[0])
        
        return self.qc

# Example usage
expression = boolean_expression
qbc = QuantumBooleanCircuit(expression)
circuit = qbc.create_circuit()
print(circuit)