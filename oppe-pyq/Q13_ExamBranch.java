import java.util.*;

/**
 * QUESTION: Abstract Classes - Staff Remuneration (July 2025 OPPE1, Question 2)
 * ============================================================================
 * Problem Statement:
 * Write a program that takes input to create an array of Staff objects and prints
 * the remuneration of each staff for their duties. Faculty should be assigned to
 * Invigilation duty, and Hod should be assigned to Squad duty.
 *
 * Abstract class Staff has:
 *   - Private instance variables: String name, String duty, int num
 *     (duty = "Invigilation" or "Squad"; num = number of hours)
 *   - Constructor to initialize the instance variables
 *   - Accessor methods: getDuty(), getNum()
 *   - Method toString() returns the name of the staff
 *   - Abstract method: abstract String remuneration()
 *
 * Class Faculty extends Staff:
 *   - Constructor to initialize instance variables
 *   - remuneration():
 *       if duty == "Invigilation": return num * 150 (as String)
 *       else: return "Wrong duty assigned"
 *
 * Class Hod extends Staff:
 *   - Constructor to initialize instance variables
 *   - remuneration():
 *       if duty == "Squad": return num * 500 (as String)
 *       else: return "Wrong duty assigned"
 *
 * Class ExamBranch has:
 *   - Method printStaffRemunerations(Staff[] sArr): prints "<name> : <remuneration>" for each
 *   - main(): reads 2 Faculty + 2 Hod (each: name duty numHours), calls printStaffRemunerations
 *
 * What you have to do: Define method printStaffRemunerations in class ExamBranch
 *
 * Test Cases:
 *   Input: Vishwanath Squad 3 / Dileep Invigilation 4 / Kavitha Invigilation 2 / Baburao Squad 4
 *   Output: Vishwanath : Wrong duty assigned
 *           Dileep : 600
 *           Kavitha : Wrong duty assigned
 *           Baburao : 2000
 *
 *   Input: Koteshwar Invigilation 3 / Koushik Invigilation 4 / Kalavathi Squad 2 / Yugandar Squad 4
 *   Output: Koteshwar : 450
 *           Koushik : 600
 *           Kalavathi : 1000
 *           Yugandar : 2000
 */

abstract class Staff {
    private String name;
    private String duty;
    private int num;
    public Staff(String name, String duty, int num) {
        this.name = name;
        this.duty = duty;
        this.num = num;
    }
    public String getDuty() {
        return duty;
    }
    public int getNum() {
        return num;
    }
    public String toString() {
        return name;
    }
    abstract String remuneration();
}

class Faculty extends Staff {
    public Faculty(String name, String duty, int num) {
        super(name, duty, num);
    }
    public String remuneration() {
        if (getDuty().equals("Invigilation"))
            return getNum() * 150 + "";
        else
            return "Wrong duty assigned";
    }
}

class Hod extends Staff {
    public Hod(String name, String duty, int num) {
        super(name, duty, num);
    }
    public String remuneration() {
        if (getDuty().equals("Squad"))
            return getNum() * 500 + "";
        else
            return "Wrong duty assigned";
    }
}

public class Q13_ExamBranch {
    // Write your solution here: Define printStaffRemunerations(Staff[] sArr)

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        Staff[] sArr = new Staff[4];
        sArr[0] = new Faculty(sc.next(), sc.next(), sc.nextInt());
        sArr[1] = new Faculty(sc.next(), sc.next(), sc.nextInt());
        sArr[2] = new Hod(sc.next(), sc.next(), sc.nextInt());
        sArr[3] = new Hod(sc.next(), sc.next(), sc.nextInt());
        printStaffRemunerations(sArr);
    }
}
