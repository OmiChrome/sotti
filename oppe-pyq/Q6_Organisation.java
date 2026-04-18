import java.util.*;

/**
 * QUESTION: Abstract Class - Employee Bonus (Sep 2023 OPPE1, Section 1.3 cont.)
 * ============================================================================
 * Problem Statement:
 * Write a Java program that, given name and salary of employees, creates an array
 * of Employee objects and prints the bonus of each employee.
 *
 * Abstract class Employee has:
 *   - Private instance variables: String name and double salary
 *   - Constructor to initialize instance variables
 *   - Accessor methods: getSalary() and getName()
 *   - Abstract method: public abstract void printBonus()
 *
 * Class Manager extends Employee:
 *   - Constructor to initialize instance variables
 *   - printBonus() prints: "<name> : <10% of salary>"  (bonus = 10% of salary)
 *
 * Class Director extends Employee:
 *   - Constructor to initialize instance variables
 *   - printBonus() prints: "<name> : <15% of salary>"  (bonus = 15% of salary)
 *
 * Class Organisation has main():
 *   - Reads name+salary of Manager, then name+salary of Director
 *   - Stores them in Employee[] array of size 2
 *   - Calls printBonus() for each
 *
 * What you have to do: Define subclasses Manager and Director
 *
 * Test Cases:
 *   Input: Ashok 30000.00 / Swaraj 40000.00   →  Output: Ashok : 3000.0 \n Swaraj : 6000.0
 *   Input: Srinivas 50000.00 / Sureka 453200.00 →  Output: Srinivas : 5000.0 \n Sureka : 67980.0
 *   Input: Rahul 40000.00 / Usha 234000.00     →  Output: Rahul : 4000.0 \n Usha : 35100.0
 *   Input: Saurab 56000.00 / Harsha 23000.00   →  Output: Saurab : 5600.0 \n Harsha : 3450.0
 */

abstract class Employee {
    private String name;
    private double salary;
    public Employee(String n, double s) {
        name = n;
        salary = s;
    }
    public double getSalary() {
        return salary;
    }
    public String getName() {
        return name;
    }
    public abstract void printBonus();
}

//********* DEFINE class Manager here
//********* DEFINE class Director here

public class Q6_Organisation {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        Employee[] eArr = new Employee[2];
        eArr[0] = new Manager(sc.nextLine(), sc.nextDouble());
        eArr[1] = new Director(sc.nextLine(), sc.nextDouble());
        eArr[0].printBonus();
        eArr[1].printBonus();
        sc.close();
    }
}
