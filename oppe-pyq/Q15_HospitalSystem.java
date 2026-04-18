import java.util.*;

/**
 * QUESTION: Inheritance - Doctor and Surgeon (July 2025 OPPE1, Question 4)
 * ============================================================================
 * Problem Statement:
 * A hospital management system maintains records of doctors and their
 * specializations. The base class Doctor has attributes for the doctor's name
 * and department. The subclass Surgeon inherits from Doctor and has an
 * additional attribute for the number of surgeries performed.
 *
 * Write a Java program that creates a Surgeon object and displays the surgeon's
 * name, department, and number of surgeries performed.
 *
 * Class Doctor has:
 *   - Private instance variables: String name and String department
 *   - Constructor to initialize the instance variables
 *   - Method toString(): returns a formatted string with doctor name and department
 *     (exact format based on test cases - likely "Name Department")
 *
 * Class Surgeon extends Doctor:
 *   - Private instance variable: int surgeries
 *   - Constructor to initialize the instance variables (name, dept, surgeries)
 *   - Override toString(): uses super.toString() and appends surgeries info
 *     (exact format based on test cases)
 *
 * Class HospitalSystem has main():
 *   - Reads: String name, String dept, int surgeries from input
 *   - Creates Surgeon object with those values
 *   - Prints the Surgeon object (calls toString())
 *
 * What you have to do:
 *   - Define constructor and toString() in Doctor
 *   - Define constructor and override toString() in Surgeon
 *
 * (Test cases not provided in PDF for this question)
 * Hint from structure: Output likely follows format:
 *   "Name Department Surgeries: <n>"  or similar
 */

class Doctor {
    private String name;
    private String department;

    // Define constructor here to initialize instance variables
    Doctor(String n,String d){name=n;department=d;}

    // Define toString() here
    public String toString(){return name+" "+department;}

}

class Surgeon extends Doctor {
    private int surgeries;

    // Define constructor here
    Surgeon(String n,String d,int s){super(n,d);surgeries=s;}

    // Override toString() here
    public String toString(){return super.toString()+" "+surgeries;}
}

public class Q15_HospitalSystem {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String name = sc.next();
        String dept = sc.next();
        int surgeries = sc.nextInt();
        Surgeon d = new Surgeon(name, dept, surgeries);
        System.out.println(d);
    }
}
