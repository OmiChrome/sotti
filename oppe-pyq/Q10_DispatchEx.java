import java.util.*;

/**
 * QUESTION: Dynamic Dispatch - Water Bodies (Sep 2024 OPPE1, Session 1 Type 3)
 * ============================================================================
 * Problem Statement:
 * Complete the Java code that uses the concept of inheritance to demonstrate
 * dynamic method dispatching.
 *
 * Class WaterBody has:
 *   - Private instance variable: name
 *   - Constructor to initialize name
 *   - Accessor method for name (getName())
 *   - Method display to print: "Inside an anonymous body of water"
 *
 * Classes River and Lake should be defined so any object of River or Lake can
 * be assigned to a reference variable of type WaterBody.
 *   - River.display() prints: "Inside river <name>"
 *   - Lake.display()  prints: "Inside lake <name>"
 *
 * Class DispatchEx main():
 *   - Creates WaterBody[] wBodies of size 3
 *   - wBodies[0] = generic WaterBody("")
 *   - wBodies[1] = River(input1)
 *   - wBodies[2] = Lake(input2)
 *   - Calls display() on each
 *
 * What you have to do:
 *   - Define accessor method getName() in WaterBody
 *   - Define method display() in WaterBody
 *   - Define classes River and Lake
 *
 * Test Cases:
 *   Input: Pamba \n Ashtamudi
 *   Output: Inside an anonymous body of water \n Inside river Pamba \n Inside lake Ashtamudi
 *
 *   Input: River Ganga \n Lake Dal
 *   Output: Inside an anonymous body of water \n Inside river River Ganga \n Inside lake Lake Dal
 *
 *   Input: The best river \n The best lake
 *   Output: Inside an anonymous body of water \n Inside river The best river \n Inside lake The best lake
 *
 *   Input: River Brahmaputra \n Lake Aries
 *   Output: Inside an anonymous body of water \n Inside river River Brahmaputra \n Inside lake Lake Aries
 */

class WaterBody {
    private String name;
    public WaterBody(String n) {
        name = n;
    }
    // Define method display
    public void display(){System.out.println("Inside an anonymous body of water");}
    // Define an accessor method getName()
    public String getName(){return name;}
}

// Define class River
class River extends WaterBody {
    River(String n){super(n);}
    public void display(){System.out.println("Inside river "+getName());}
}

// Define class Lake
class Lake extends WaterBody {
    Lake(String n){super(n);}
    public void display(){System.out.println("Inside lake "+getName());}
}

public class Q10_DispatchEx {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        WaterBody[] wBodies = new WaterBody[3];
        wBodies[0] = new WaterBody("");
        wBodies[1] = new River(sc.nextLine());
        wBodies[2] = new Lake(sc.nextLine());
        wBodies[0].display();
        wBodies[1].display();
        wBodies[2].display();
        sc.close();
    }
}
