import java.util.Scanner;

/**
 * QUESTION: Abstract Classes and Interfaces - Research Scholar (Sep 2023 OPPE1)
 * ============================================================================
 * Problem Statement:
 * Complete the Java program to demonstrate the use of abstract classes and
 * interfaces. You have to complete the definition of classes JuniorRS and
 * SeniorRS to obtain the output as given in the public test cases.
 *
 * - Interface IResearchScholar has two methods:
 *     public void teaches(String str)
 *     public void studies(String str)
 * - Define classes JuniorRS and SeniorRS such that:
 *     JuniorRS implements IResearchScholar
 *     SeniorRS extends JuniorRS
 * - Class InterAbstrTest extends SeniorRS, and has the main method.
 *     An object of JuniorRS invokes studies(), an object of SeniorRS invokes
 *     studies() and teaches().
 *
 * Test Cases:
 *   Input: Python \n Java   →  Output: TA studies Python \n TA studies Java \n TA teaches Java
 *   Input: Cloud computing \n Data Mining
 *       → Output: TA studies Cloud computing \n TA studies Data Mining \n TA teaches Data Mining
 *   Input: Machine Learning \n Machine Learning
 *       → Output: TA studies Machine Learning \n TA studies Machine Learning \n TA teaches Machine Learning
 */

interface IResearchScholar {
    public void teaches(String str);
    public void studies(String str);
}

abstract class JuniorRS implements IResearchScholar {
    public void studies(String str) {
        System.out.println("TA studies " + str);
    }
}

class SeniorRS extends JuniorRS {
    public void teaches(String str) {
        System.out.println("TA teaches " + str);
    }
}

public class Q2_InterAbstrTest extends SeniorRS {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String str1 = sc.nextLine();
        String str2 = sc.nextLine();
        JuniorRS jrs = new Q2_InterAbstrTest();
        SeniorRS srs = new Q2_InterAbstrTest();
        jrs.studies(str1);
        srs.studies(str2);
        srs.teaches(str2);
        sc.close();
    }
}
