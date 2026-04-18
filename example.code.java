import java.util.*;
class Doctor {
    private String name;
    private String department;

    // Define constructor here to initialize instance variables
    // Define toString() here

}

class Surgeon extends Doctor {
    private int surgeries;
    // Define constructor here
    // Override toString() here
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
