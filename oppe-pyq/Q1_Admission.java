import java.util.*;

/**
 * QUESTION: Copy Constructor (BSCCS2005 Sep 2023 OPPE1 - Session 2, Type 1)
 * ============================================================================
 * Problem Statement:
 * In a college, Student s1 chooses a set of courses. Student s2 also chooses all
 * the courses chosen by s1 except the second course, in place of which s2 chooses
 * another course. Write a program that defines two classes Student and Admission.
 * Define copy constructor to create s2 from s1 such that changing the values of
 * instance variables of either s2 or s1 does not affect the other one.
 * The code takes name of student s2 and the new course chosen by s2 as input.
 *
 * Class Student has/should have:
 *   - Private instance variables: String name and String[] courses
 *   - Define required constructor(s)
 *   - Accessor methods: getName() and getCourses(int)
 *   - Mutator methods: setName(String) and setCourses(int, String)
 *
 * Class Admission has method main that:
 *   - Creates two objects s1 and s2 (s2 is created using copy constructor from s1)
 *   - Updates name of s2 and second course of s2 from input
 *   - Prints: name of s1, name of s2, second course of s1, second course of s2
 *
 * What you have to do: Define constructor(s) in class Student
 *
 * Test Cases:
 *   Input: Suba COA  →  Output: Nandu: DL \n Suba: COA
 *   Input: Pai CV    →  Output: Nandu: DL \n Pai: CV
 *   Input: Neha DS   →  Output: Nandu: DL \n Neha: DS
 */

class Student {
    String name;
    String[] courses;

    //***** Define constructor(s) here

    public void setName(String n) {
        name = n;
    }
    public void setCourses(int indx, String c) {
        courses[indx] = c;
    }
    public String getName() {
        return name;
    }
    public String getCourses(int indx) {
        return courses[indx];
    }
}

public class Q1_Admission {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String[] courses = {"Maths", "DL", "DSA", "DC"};
        Student s1 = new Student("Nandu", courses);
        Student s2 = new Student(s1);
        s2.setName(sc.next());
        s2.setCourses(1, sc.next());
        System.out.println(s1.getName() + ": " + s1.getCourses(1));
        System.out.println(s2.getName() + ": " + s2.getCourses(1));
    }
}
